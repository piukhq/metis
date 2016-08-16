import httpretty
import json
import settings
from flask.ext.testing import TestCase
from app import create_app
from unittest.mock import patch

auth_key = 'Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL' \
           'CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU'


class Testing:
    TESTING = True


class TestMetisResources(TestCase):
    def create_app(self):
        return create_app(Testing)

    def test_create_receiver(self):
        resp = self.client.post('/payment_service/create_receiver',
                                headers={'content-type': 'application/json'},
                                data=json.dumps({"receiver_type": "test", "hostname": "http://latestserver.com"}))
        self.assertTrue(resp.status_code == 201)

    def test_create_receiver_invalid_hostname(self):
        resp = self.client.post('/payment_service/create_receiver',
                                headers={'content-type': 'application/json'},
                                data=json.dumps({"hostname": "testing"}))
        self.assertTrue(resp.status_code == 422)

    def test_create_amex_receiver(self):
        resp = self.client.post('/payment_service/create_receiver',
                                headers={'content-type': 'application/json'},
                                data=json.dumps({"receiver_type": "american_express"}))
        self.assertTrue(resp.status_code == 201)

    @patch('app.auth.parse_token')
    def test_amex_receiver(self, mock_parse_token):
        settings.TESTING = False
        mock_parse_token.return_value = "{'sub':''45'}"

        resp = self.client.post('/payment_service/register_card',
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps({"partner_slug": "amex",
                                                 "payment_token": "3ERtq3pUV5OiNpdTCuhhXLBmnv8"}))
        self.assertTrue(resp.status_code == 200)

    def test_amex_receiver_auth_401(self):
        settings.TESTING = False
        resp = self.client.post('/payment_service/register_card',
                                headers={'content-type': 'application/json'},
                                data=json.dumps({"partner_slug": "amex",
                                                 "payment_token": "3ERtq3pUV5OiNpdTCuhhXLBmnv8"}))
        self.assertTrue(resp.status_code == 401)

    def test_spreedly_callback(self):
        settings.TESTING = True
        settings.SPREEDLY_SIGNING_SECRET = 'RKOCG5D8D3fZxDSg504D0IxU2XD4Io5VXmyzdCtTivHFTTSylzM2ZzTWFwVH4ucG'

        log = """    <transactions>
          <transaction>
            <amount type="integer">100</amount>
            <on_test_gateway type="boolean">false</on_test_gateway>
            <created_at type="datetime">2012-09-10T20:35:10Z</created_at>
            <updated_at type="datetime">2012-09-10T20:35:11Z</updated_at>
            <currency_code>USD</currency_code>
            <succeeded type="boolean">true</succeeded>
            <state>succeeded</state>
            <token>5AG4P7FPjlfIA6aED6AgZvUEehx</token>
            <transaction_type>OffsitePurchase</transaction_type>
            <order_id nil="true"></order_id>
            <ip nil="true"></ip>
            <callback_url>http://example.com/handle_callback</callback_url>
            <signed>
              <signature>b81436daf0d695404c5bf7a2aecf049d460bb6e1</signature>
              <fields>amount callback_url created_at currency_code ip on_test_gateway order_id state succeeded token transaction_type updated_at</fields>
              <algorithm>sha1</algorithm>
            </signed>
          </transaction>
        </transactions>"""  # noqa
        """noqa comment prevents flake8 checking the previous string."""

        resp = self.client.post('/payment_service/notify/spreedly',
                                headers={'content-type': 'application/xml'},
                                data=log)
        self.assertTrue(resp.status_code == 200)
