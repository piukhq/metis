import json
import settings
from flask.ext.testing import TestCase
from app import create_app


class Testing:
    TESTING = True


class TestMetisResources(TestCase):
    def create_app(self):
        return create_app(Testing)

    def test_create_receiver(self):
        resp = self.client.post('/create_receiver',
                                headers={'content-type': 'application/json'},
                                data=json.dumps({"hostname": "http://latestserver.com"}))
        self.assertTrue(resp.status_code == 201)

    def test_create_receiver_invalid_hostname(self):
        resp = self.client.post('/create_receiver',
                                headers={'content-type': 'application/json'},
                                data=json.dumps({"hostname": "testing"}))
        self.assertTrue(resp.status_code == 422)

    def test_amex_receiver(self):
        settings.TESTING = True
        resp = self.client.post('/register_card',
                                headers={'content-type': 'application/json'},
                                data=json.dumps({"partner_slug": "amex",
                                                 "payment_token": "RUcZ9XTPekFKL5DK0WC651xnWgV"}))
        self.assertTrue(resp.status_code == 200)
