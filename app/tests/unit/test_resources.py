import httpretty
import json
import settings
import app.agents.mastercard as mc
from flask.ext.testing import TestCase
from app import create_app
from unittest.mock import patch

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

    @patch('app.auth.parse_token')
    @httpretty.activate
    def test_end_site_receiver(self, mock_parse_token):
        settings.TESTING = True
        mock_parse_token.return_value = "{'sub':''45'}"
        mc.testing_receiver_token = self.receiver_token
        self.end_site_receiver_route()
        resp = self.client.post('/payment_service/register_card',
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps({"partner_slug": "mastercard",
                                                 "payment_token": "12345678901234567890"}))
        self.assertTrue(resp.status_code == 200)

    @patch('app.auth.parse_token')
    @httpretty.activate
    def test_end_site_receiver_invalid_param(self, mock_parse_token):
        mock_parse_token.return_value = "{'sub':''45'}"
        self.end_site_receiver_route()
        resp = self.client.post('/payment_service/register_card',
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps({}))
        self.assertTrue(resp.status_code == 400)

    @patch('app.auth.parse_token')
    @httpretty.activate
    def test_end_site_receiver_param_missing(self, mock_parse_token):
        mock_parse_token.return_value = "{'sub':''45'}"
        self.end_site_receiver_route()
        resp = self.client.post('/payment_service/register_card',
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps({"partner_slug": "mastercard"}))
        self.assertTrue(resp.status_code == 400)

    @patch('app.auth.parse_token')
    @httpretty.activate
    def test_end_site_blank_param(self, mock_parse_token):
        mock_parse_token.return_value = "{'sub':''45'}"
        self.end_site_receiver_route()
        resp = self.client.post('/payment_service/register_card',
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps({"partner_slug": "mastercard",
                                                 "payment_token": " "}))
        self.assertTrue(resp.status_code == 400)
