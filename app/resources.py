import arrow
import json
from app.services import create_prod_receiver
from flask_restful import Resource, Api
from flask import request, make_response
from app.agents.agent_manager import AgentManager
from app.auth import authorized
from app.card_router import process_card, ActionCode
from settings import logger

api = Api()


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
            # payment_token = Spreedly payment method token
            # card_token = Bink token - shorter than Spreedly's, because of Visa Inc limit.
            # id = the hermes database card id. Used for setting status back in Hermes.
            card_info = {
                'id': req_data['id'],
                'payment_token': req_data['payment_token'],
                'card_token': req_data['card_token'],
                'partner_slug': req_data['partner_slug'],
            }
        except KeyError:
            return make_response('Request parameters not complete', 400)

        process_card(action_code, card_info)

        return make_response('Success', 200)

    @authorized
    def post(self):
        return self.action(ActionCode.ADD)

    @authorized
    def delete(self):
        return self.action(ActionCode.DELETE)


api.add_resource(PaymentCard, '/payment_service/payment_card')


class Notify(Resource):
    # This callback needs to respond within 5 seconds of receiving a request from Spreedly.
    # Therefore setup async. call to save data, and return 200 response to Spreedly.

    def post(self, provider_slug):
        req_data = request.data
        response_text = 'OK'
        status_code = 200
        # Process the incoming response async.
        # Write to Cassandra?

        try:
            agent_instance = AgentManager.get_agent(provider_slug)

            agent_instance.save(req_data)
        except Exception as e:
            response_text = str({'Error': 'Problem processing request. Message: {}'.format(e)})
            status_code = 400

        return make_response(response_text, status_code)

api.add_resource(Notify, '/payment_service/notify/<string:provider_slug>')
