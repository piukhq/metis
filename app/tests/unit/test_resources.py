import httpretty
import json
import settings
import app.agents.mastercard as mc
from flask.ext.testing import TestCase
from app import create_app


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

    @httpretty.activate
    def test_create_receiver(self):
        self.create_receiver_route()
        resp = self.client.post('/payment_service/create_receiver',
                                headers={'content-type': 'application/json'},
                                data=json.dumps({"hostname": "http://latestserver.com", "receiver_type": "test"}))
        self.assertTrue(resp.status_code == 201)

    @httpretty.activate
    def test_create_receiver_invalid_hostname(self):
        self.create_receiver_route()
        resp = self.client.post('/payment_service/create_receiver',
                                headers={'content-type': 'application/json'},
                                data=json.dumps({}))
        self.assertTrue(resp.status_code == 422)

    @httpretty.activate
    def test_end_site_receiver(self):
        settings.TESTING = True
        mc.testing_receiver_token = self.receiver_token
        self.end_site_receiver_route()
        resp = self.client.post('/payment_service/register_card',
                                headers={'content-type': 'application/json'},
                                data=json.dumps({"partner_slug": "mastercard",
                                                 "payment_token": "12345678901234567890"}))
        self.assertTrue(resp.status_code == 200)

    @httpretty.activate
    def test_end_site_receiver_invalid_param(self):
        self.end_site_receiver_route()
        resp = self.client.post('/payment_service/register_card',
                                headers={'content-type': 'application/json'},
                                data=json.dumps({}))
        self.assertTrue(resp.status_code == 400)

    @httpretty.activate
    def test_end_site_receiver_param_missing(self):
        self.end_site_receiver_route()
        resp = self.client.post('/payment_service/register_card',
                                headers={'content-type': 'application/json'},
                                data=json.dumps({"partner_slug": "mastercard"}))
        self.assertTrue(resp.status_code == 400)

    @httpretty.activate
    def test_end_site_blank_param(self):
        self.end_site_receiver_route()
        resp = self.client.post('/payment_service/register_card',
                                headers={'content-type': 'application/json'},
                                data=json.dumps({"partner_slug": "mastercard",
                                                 "payment_token": " "}))
        self.assertTrue(resp.status_code == 400)
