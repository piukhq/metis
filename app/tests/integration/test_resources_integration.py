import json
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
