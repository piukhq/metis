import httpretty
import json
import settings
import app.agents.mastercard as mc
from flask.ext.testing import TestCase
from app import create_app
from unittest.mock import patch

from app.card_router import ActionCode

auth_key = 'Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL' \
           'CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU'


class Testing:
    TESTING = True


class TestMetisResources(TestCase):
    xml_response = '<receiver>' \
        '<receiver_type>test1</receiver_type>' \
        '</receiver>'

    receiver_token = "testing_624624613fgae3"

    def create_app(self):
        return create_app(Testing)

    def create_receiver_route(self):
        url = 'https://core.spreedly.com/v1/receivers.xml'
        httpretty.register_uri(httpretty.POST, url,
                               status=201,
                               body=self.xml_response,
                               content_type='application/xml')

    def end_site_receiver_route(self):
        url = 'https://core.spreedly.com/v1/receivers/' + self.receiver_token + '/deliver.xml'
        httpretty.register_uri(httpretty.POST, url,
                               status=200,
                               body=self.xml_response,
                               content_type='application/xml')

    @patch('app.auth.parse_token')
    @httpretty.activate
    def test_create_receiver(self, mock_parse_token):
        mock_parse_token.return_value = "{'sub':''45'}"
        self.create_receiver_route()
        resp = self.client.post('/payment_service/create_receiver',
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps({"receiver_type": "test"}))
        self.assertTrue(resp.status_code == 201)

    @patch('app.auth.parse_token')
    @httpretty.activate
    def test_create_receiver_invalid_hostname(self, mock_parse_token):
        mock_parse_token.return_value = "{'sub':''45'}"
        self.create_receiver_route()
        resp = self.client.post('/payment_service/create_receiver',
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps({}))
        self.assertTrue(resp.status_code == 422)

    @patch('app.resources.process_card')
    @patch('app.auth.parse_token')
    @httpretty.activate
    def test_end_site_receiver(self, mock_parse_token, mock_process_card):
        test_card = {
            'id': 1,
            'payment_token': '1111111111111111111111',
            'card_token': '1111111111111111111111',
            'partner_slug': 'mastercard',
            'date': 1475920002
        }
        settings.TESTING = True
        mock_parse_token.return_value = "{'sub':''45'}"
        mc.testing_receiver_token = self.receiver_token
        self.end_site_receiver_route()
        resp = self.client.post('/payment_service/payment_card',
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps(test_card))
        self.assertEqual(resp.status_code, 200)
        mock_process_card.assert_called_with(ActionCode.ADD, test_card)

    @patch('app.auth.parse_token')
    @httpretty.activate
    def test_end_site_receiver_invalid_param(self, mock_parse_token):
        mock_parse_token.return_value = "{'sub':''45'}"
        self.end_site_receiver_route()
        resp = self.client.post('/payment_service/payment_card',
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps({}))
        self.assertEqual(resp.status_code, 400)

    @patch('app.auth.parse_token')
    @httpretty.activate
    def test_end_site_receiver_param_missing(self, mock_parse_token):
        mock_parse_token.return_value = "{'sub':''45'}"
        self.end_site_receiver_route()
        resp = self.client.post('/payment_service/payment_card',
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps({"partner_slug": "mastercard"}))
        self.assertTrue(resp.status_code == 400)

    @patch('app.auth.parse_token')
    @httpretty.activate
    def test_end_site_blank_param(self, mock_parse_token):
        test_card = {
            'id': 1,
            'payment_token': '',
            'card_token': '1111111111111111111111',
            'partner_slug': 'visa',
            'date': 1475920002
        }
        mock_parse_token.return_value = "{'sub':''45'}"
        self.end_site_receiver_route()
        resp = self.client.post('/payment_service/payment_card',
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps(test_card))
        self.assertTrue(resp.status_code == 400)

    @patch('app.agents.spreedly.payment_card_notify')
    def test_spreedly_notify(self, mock_payment_card_notify):
        json = '''{
  "transactions": [
    {
      "token": "OZCXojxhJki4Ch8CINYg2Iw58An",
      "transaction_type": "ExportPaymentMethods",
      "state": "completed",
      "created_at": "2016-10-07T15:01:18Z",
      "updated_at": "2016-10-07T15:01:19Z",
      "succeeded": true,
      "message": "Succeeded",
      "payment_methods_submitted": [
        "Q5zPG5NbwmUujR8IOrte9ds6BlK",
        "ELKQxIL9lCdjjfujUzYXTtnqEp8",
        "badCardToken"
      ],
      "payment_method_data": null,
      "payment_methods_included": [
        "Q5zPG5NbwmUujR8IOrte9ds6BlK",
        "ELKQxIL9lCdjjfujUzYXTtnqEp8"
      ],
      "encode_response": null,
      "callback_url": "https://example.com",
      "url": "sftp://posttestserver.com/path/to/filename.txt",
      "payment_methods_excluded": [
        {
          "badCardToken": "Unable to find the specified payment method."
        }
      ],
      "receiver": {
        "receiver_type": "test",
        "token": "OJDBOWuRDIZ2GlXKpxBxfU9AwIV",
        "hostnames": "sftp://posttestserver.com",
        "state": "retained",
        "created_at": "2016-10-07T15:01:18Z",
        "updated_at": "2016-10-07T15:01:18Z",
        "credentials": null,
        "protocol": {
          "user": "user"
        }
      }
    }
  ]
}'''
        mock_payment_card_notify.return_value = 'Slack called'
        resp = self.client.post('/payment_service/notify/spreedly',
                                headers={'Content-Type': 'application/json'},
                                data=json)

        self.assertEqual(resp.status_code, 200)
