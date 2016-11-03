import httpretty
import json
import settings
import app.agents.visa as agent
import logging
from unittest import TestCase
from app.tests.unit.fixture import card_info, card_info_reduce
from testfixtures import log_capture


class Testing:
    TESTING = True


class TestVisa(TestCase):

    def spreedly_route(self):
        url = 'https://core.spreedly.com/v1/receivers/JKzJSKICIOZodDBMCyuRmttkRjO/export.json'
        httpretty.register_uri(httpretty.POST, url,
                               status=200,
                               body=json.dumps({"transaction": {
                                   "token": "123456789",
                                   "transaction_type": "ExportPaymentMethods",
                                   "state": "succeeded"}}),
                               content_type='application/json')

    def setUp(self):
        self.visa = agent.Visa()
        self.logger = logging.getLogger()
        self.orig_handlers = self.logger.handlers
        self.logger.handlers = []
        self.level = self.logger.level

    def tearDown(self):
        self.logger.handlers = self.orig_handlers
        self.logger.level = self.level

    def test_receiver_token_testing(self):
        settings.TESTING = True
        result = self.visa.receiver_token()
        self.assertIn('JKzJSKICIOZodDBMCyuRmttkRjO', result)

    def test_receiver_token_production(self):
        settings.TESTING = False
        result = self.visa.receiver_token()
        self.assertIn('HwA3Nr2SGNEwBWISKzmNZfkHl6D', result)

    def test_request_header_both(self):
        result = self.visa.request_header()
        self.assertIn('json', result)

    def test_create_file_data(self):
        cards = [1234, 5678, 9876]
        result = self.visa.create_file_data(cards)
        self.assertIn('{{external_cardholder_id}}', result)
        self.assertIn('{{credit_card_number}}', result)

    @httpretty.activate
    @log_capture(level=logging.INFO)
    def test_create_cards(self, l):
        settings.TESTING = True
        self.spreedly_route()
        self.visa.create_cards(card_info)
        message = 'Visa batch successful'
        self.assertTrue(any(message in r.msg for r in l.records))

    def test_request_body_json(self):
        settings.TESTING = True
        result = self.visa.request_body(card_info_reduce)
        self.assertIn('111111111111112', result)
        self.assertIn('{{#gpg}}', result)
        self.assertIn('{{credit_card_number}}', result)
