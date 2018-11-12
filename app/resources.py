import arrow
import json
from app.services import create_prod_receiver, retain_payment_method_token
from flask_restful import Resource, Api
from flask import request, make_response
from app.agents.agent_manager import AgentManager
from app.auth import authorized
from app.card_router import process_card, ActionCode
from settings import logger
from voluptuous import Schema, Required, MultipleInvalid, All, Length

api = Api()

card_info_schema = Schema({
    Required('id'): int,
    Required('payment_token'): All(str, Length(min=1)),
    Required('card_token'): All(str, Length(min=1)),
    Required('date'): int,
    Required('partner_slug'): All(str, Length(min=1)),
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
        logger.info('{} Received {} payment card request: {}'.format(arrow.now(), action_name, req_data))

        try:
            card_info_schema(req_data)
        except MultipleInvalid:
            return make_response('Request parameters not complete', 400)

        if action_code == ActionCode.ADD:
            resp = retain_payment_method_token(req_data['payment_token'])
            if resp.status_code != 200:
                logger.info('Retain unsuccessful : {}'.format(req_data['payment_token']))
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
