import httpretty
import json
import logging
import os
from unittest import TestCase, mock

from testfixtures import log_capture

os.environ['METIS_TESTING'] = 'True'
os.environ['VISA_RECEIVER_TOKEN'] = 'JKzJSKICIOZodDBMCyuRmttkRjO'
from app.tests.unit.fixture import card_info_reduce  # noqa
from app.card_router import ActionCode  # noqa
from app.agents.visa import Visa  # noqa
import settings  # noqa

auth_key = 'Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL' \
           'CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU'


class TestVisa(TestCase):
    mock_get_next_seq_number = mock.Mock()
    mock_get_next_seq_number.return_value = 1

    def spreedly_route(self):
        url = 'https://core.spreedly.com/v1/receivers/JKzJSKICIOZodDBMCyuRmttkRjO/export.json'
        httpretty.register_uri(httpretty.POST, url,
                               status=200,
                               body=json.dumps({"transaction": {
                                   "token": "123456789",
                                   "transaction_type": "ExportPaymentMethods",
                                   "state": "succeeded"}}),
                               content_type='application/json')

    def hermes_status_route(self):
        httpretty.register_uri(httpretty.PUT,
                               '{}/payment_cards/accounts/status'.format(settings.HERMES_URL),
                               status=200,
                               headers={'Authorization': auth_key},
                               body=json.dumps({"status_code": 200, "message": "success"}),
                               content_type='application/json')

    def setUp(self):
        self.visa = Visa()
        self.logger = logging.getLogger()
        self.orig_handlers = self.logger.handlers
        self.logger.handlers = []
        self.level = self.logger.level

    def tearDown(self):
        self.logger.handlers = self.orig_handlers
        self.logger.level = self.level

    def test_receiver_token_testing(self):
        result = self.visa.receiver_token()
        self.assertIn('JKzJSKICIOZodDBMCyuRmttkRjO', result)

    def test_request_header_both(self):
        result = self.visa.request_header()
        self.assertIn('json', result)

    @mock.patch.object(Visa, 'get_next_seq_number', mock_get_next_seq_number)
    def test_create_file_data(self):
        cards = [1234, 5678, 9876]
        result = self.visa.create_file_data(cards)
        self.assertIn('{{external_cardholder_id}}', result)
        self.assertIn('{{credit_card_number}}', result)

    @mock.patch.object(Visa, 'get_next_seq_number', mock_get_next_seq_number)
    @httpretty.activate
    @log_capture(level=logging.INFO)
    def test_create_cards(self, l):
        card_info_add = [{
            'id': 1,
            'payment_token': '1111111111111111111112',
            'card_token': '111111111111112',
            'partner_slug': 'test_slug',
            'action_code': ActionCode.ADD,
            'date': 1475920002
        }, {
            'id': 2,
            'payment_token': '1111111111111111111113',
            'card_token': '111111111111113',
            'partner_slug': 'test_slug',
            'action_code': ActionCode.ADD,
            'date': 1475920002
        }]

        self.spreedly_route()
        self.hermes_status_route()
        self.visa.create_cards(card_info_add)
        message = 'Visa batch successful'
        self.assertTrue(any(message in r.msg for r in l.records))

    @mock.patch.object(Visa, 'get_next_seq_number', mock_get_next_seq_number)
    def test_request_body_json(self):
        result, file_name = self.visa.request_body(card_info_reduce)
        self.assertIn('111111111111112', result)
        self.assertIn('{{#gpg}}', result)
        self.assertIn('{{credit_card_number}}', result)
        self.assertTrue(len(file_name))
