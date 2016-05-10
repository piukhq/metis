import json
from app.services import create_receiver, end_site_receiver
from flask_restful import Resource, Api
from flask import request, make_response

# from app.celery_client import add_together

api = Api()


class CreateReceiver(Resource):
    def post(self):
        req_data = json.loads(request.data.decode())
        if req_data is not None and len(req_data) > 0:
            result = create_receiver(req_data['hostname'])
            response_text = result.text
            status_code = 201
        else:
            response_text = str({'Error': 'Please provide the hostname url.'})
            status_code = 422

        return make_response(response_text, status_code)

api.add_resource(CreateReceiver, '/create_receiver')


class RegisterCard(Resource):
    def post(self):
        req_data = json.loads(request.data.decode())
        # Validate input parameters here? Could use something like Marshmallow (overkill?) for serializing.
        try:
            result = end_site_receiver(req_data['partner_slug'], req_data['payment_token'])
            response_text = result.text
            status_code = 200
        except Exception as e:
            response_text = str({'Error': 'Problem sending the payment card information. Message: {}'.format(e)})
            status_code = 400

        return make_response(response_text, status_code)

api.add_resource(RegisterCard, '/register_card')
