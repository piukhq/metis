import json
from app.services import create_receiver, end_site_receiver
from flask_restful import Resource, Api
from flask import request, make_response
from app.agents.agent_manager import AgentManager
# from app.celery_client import add_together

api = Api()


class CreateReceiver(Resource):
    def post(self):
        req_data = json.loads(request.data.decode())
        if req_data is not None and len(req_data) > 0:
            result = create_receiver(req_data['hostname'], req_data['receiver_type'])
            response_text = result.text
            status_code = result.status_code
        else:
            response_text = str({'Error': 'Please provide the hostname url.'})
            status_code = 422

        return make_response(response_text, status_code)

api.add_resource(CreateReceiver, '/payment_service/create_receiver')


class RegisterCard(Resource):
    def post(self):
        req_data = json.loads(request.data.decode())
        # Validate input parameters here? Could use something like Marshmallow (overkill?) for serializing.
        try:
            result = end_site_receiver(req_data['partner_slug'], req_data['payment_token'])
            response_text = result.content
            status_code = result.status_code
        except Exception as e:
            response_text = str({'Error': 'Problem sending the payment card information. Message: {}'.format(e)})
            status_code = 400

        return make_response(response_text, status_code)

api.add_resource(RegisterCard, '/payment_service/register_card')


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
