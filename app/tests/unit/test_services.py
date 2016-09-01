import app.agents.mastercard as mc
import unittest
import httpretty
import settings
from app.services import create_receiver, add_card


class TestServices(unittest.TestCase):

    create_url = 'https://core.spreedly.com/v1/receivers.xml'
    payment_method_token = '3rkN9aJFfNEjvr2LqYZE4606hgG'
    receiver_token = 'aDwu4ykovZVe7Gpto3rHkYWI5wI'
    payment_url = 'https://core.spreedly.com/v1/receivers/' + receiver_token + '/deliver.xml'

    def create_route(self):
        xml_response = '<receiver>' \
                   '<receiver_type>test</receiver_type>' \
                   '<token>aDwu4ykovZVe7Gpto3rHkYWI5wI</token>' \
                   '<hostnames>http://testing_latestserver.com</hostnames>' \
                   '<state>retained</state>' \
                   '<created_at type="dateTime">2016-04-06T07:54:13Z</created_at>' \
                   '<updated_at type="dateTime">2016-04-06T07:54:13Z</updated_at>' \
                   '<credentials nil="true"/>' \
                   '</receiver>'

        httpretty.register_uri(httpretty.POST, self.create_url,
                               status=201,
                               body=xml_response,
                               content_type='application/xml')

    def test_route(self):
        xml_data = '<delivery>' \
                   '<state>testing</state>' \
                   '</delivery>'

        httpretty.register_uri(httpretty.POST, self.payment_url,
                               status=200,
                               body=xml_data,
                               content_type='application/xml')

    @httpretty.activate
    def test_create_receiver(self):
        self.create_route()
        resp = create_receiver('http://testing_latestserver.com', 'test')
        self.assertTrue(resp.status_code == 201)
        self.assertIn('token', resp.text)

    @httpretty.activate
    def test_add_card(self):
        card_info = [{
            'payment_token': '1111111111111111111111',
            'card_token': '111111111111112',
            'partner_slug': 'mastercard'
        }]

        self.test_route()
        mc.testing_receiver_token = self.receiver_token
        settings.TESTING = True
        resp = add_card(card_info)
        self.assertTrue(resp.status_code == 200)
