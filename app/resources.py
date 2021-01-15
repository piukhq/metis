import json

import arrow
from flask import request, make_response
from flask_restful import Resource, Api
from voluptuous import Schema, Required, Optional, MultipleInvalid, All, Length

from app.action import ActionCode
from app.agents.agent_manager import AgentManager
from app.agents.visa_offers import Visa
from app.auth import authorized
from app.card_router import process_card
from app.services import create_prod_receiver, retain_payment_method_token
from settings import logger

api = Api()

card_info_schema = Schema({
    Required('id'): int,
    Required('payment_token'): All(str, Length(min=1)),
    Required('card_token'): All(str, Length(min=1)),
    Required('date'): int,
    Required('partner_slug'): All(str, Length(min=1)),
    Optional('retry_id'): int,
    Optional('activations'): dict
})


class Healthz(Resource):
    def get(self):
        return ''


api.add_resource(Healthz, '/healthz')


class CreateReceiver(Resource):

    @authorized
    def post(self):
        req_data = json.loads(request.data.decode())
        if req_data is not None and len(req_data) > 0:
            result = create_prod_receiver(req_data['receiver_type'])
            response_text = result.text
            status_code = result.status_code
        else:
            response_text = str({'Error': 'Please provide the hostname url.'})
            status_code = 422

        return make_response(response_text, status_code)


api.add_resource(CreateReceiver, '/payment_service/create_receiver')


class PaymentCard(Resource):

    def action(self, action_code):
        req_data = json.loads(request.data.decode())

        action_name = {ActionCode.ADD: 'add', ActionCode.DELETE: 'delete'}[action_code]
        try:
            card_info_schema(req_data)
        except MultipleInvalid:
            logger.error(f'{arrow.now()} Received {action_name} payment card request failed '
                         f'- invalid schema: {req_data}')
            return make_response('Request parameters not complete', 400)

        logger.info('{} Received {} payment card request: {}'.format(arrow.now(), action_name, req_data))
        if action_code == ActionCode.ADD:
            status_code = 500
            resp_text = f" No reply received"
            try:
                resp = retain_payment_method_token(req_data['payment_token'], req_data.get('partner_slug'))
                status_code = resp.status_code
                reason = resp.reason
                resp_text = resp.text
            except AttributeError:
                status_code = 504
                reason = "Connection failed after retry"
            except Exception as e:
                status_code = 500
                reason = "Exception {e}"

            if status_code != 200:
                logger.info(f'Retain unsuccessful: HTTP {status_code} {reason} {resp_text}'
                            f'Payment token: {req_data.get("payment_token")} partner: {req_data.get("partner_slug")}')
                return make_response('Retain unsuccessful', 400)

        process_card(action_code, req_data)

        return make_response('Success', 200)

    @authorized
    def post(self):
        return self.action(ActionCode.ADD)

    @authorized
    def delete(self):
        return self.action(ActionCode.DELETE)


api.add_resource(PaymentCard, '/payment_service/payment_card')


class PaymentCardUpdate(Resource):

    @authorized
    def post(self):
        req_data = json.loads(request.data.decode())

        logger.info('{} Received reactivate payment card request: {}'.format(arrow.now(), req_data))

        try:
            card_info_schema(req_data)
        except MultipleInvalid:
            return make_response('Request parameters not complete', 400)

        process_card(ActionCode.REACTIVATE, req_data)

        return make_response('Success', 200)


api.add_resource(PaymentCardUpdate, '/payment_service/payment_card/update')


class Notify(Resource):
    # This callback needs to respond within 5 seconds of receiving a request from Spreedly.
    # Therefore setup async. call to save data, and return 200 response to Spreedly.

    def post(self, provider_slug):
        req_data = request.json

        agent_instance = AgentManager.get_agent(provider_slug)
        agent_instance.save(req_data)

        return make_response('OK', 200)


api.add_resource(Notify, '/payment_service/notify/<string:provider_slug>')


class VisaActivate(Resource):

    @staticmethod
    def post():
        visa = Visa()
        response_status, status_code, agent_response_code, agent_message, other_data = visa.activate_card(request.json)
        response = make_response(json.dumps({
            'response_status': response_status,
            'agent_response_code': agent_response_code,
            'agent_response_message': agent_message,
            'activation_id': other_data.get('activation_id', "")
        }), status_code)
        response.headers['Content-Type'] = 'application/json'
        return response


api.add_resource(VisaActivate, '/visa/activate/')


class VisaDeactivate(Resource):

    @staticmethod
    def post():
        visa = Visa()
        response_status, status_code, agent_response_code, agent_message, _ = visa.deactivate_card(request.json)
        response = make_response(json.dumps({
            'response_status': response_status,
            'agent_response_code': agent_response_code,
            'agent_response_message': agent_message
        }), status_code)
        response.headers['Content-Type'] = 'application/json'
        return response


api.add_resource(VisaDeactivate, '/visa/deactivate/')
