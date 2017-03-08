import httpretty
import json
import logging
import os
from unittest import TestCase, mock
import arrow
from testfixtures import log_capture

os.environ['METIS_TESTING'] = 'True'
os.environ['VISA_RECEIVER_TOKEN'] = 'JKzJSKICIOZodDBMCyuRmttkRjO'
from app.tests.unit.fixture import card_info_reduce  # noqa
from app.card_router import ActionCode  # noqa
from app.agents.visa import Visa, VisaCardFile, Header, Footer  # noqa
import settings  # noqa

auth_key = 'Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL' \
           'CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU'


class TestVisa(TestCase):
    mock_get_next_seq_number = mock.Mock()
    mock_get_next_seq_number.return_value = 1

    def spreedly_route(self):
        url = 'https://core.spreedly.com/v1/receivers/visa/export.json'
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

        self.card_info_add = [{
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

        self.cards = [1234, 5678, 9876]

        self.header = Header(
            source_id='LOYANG',
            destination_id='VISA',
            file_description='Bink user card registration information',
            file_create_date=self.visa.format_datetime(arrow.now()),
            file_control_number=str(1).rjust(2, '0'),
            file_format_version='2.0',
            not_used1='',
            not_used2='',
            filler1='',
            filler2='',
            file_type_indicator='I',
            file_unique_text='Bink user card data',
            filler3=''
        )

        self.footer = Footer(
            record_count=str(len(self.cards)).rjust(10, '0'),
            filler=''
        )

        self.vcf = VisaCardFile()

    def tearDown(self):
        self.logger.handlers = self.orig_handlers
        self.logger.level = self.level

    def test_request_header_both(self):
        result = self.visa.request_header()
        self.assertIn('json', result)

    @mock.patch.object(Visa, 'get_next_seq_number', mock_get_next_seq_number)
    def test_create_file_data(self):
        result = self.visa.create_file_data(self.cards)
        self.assertIn('{{external_cardholder_id}}', result)
        self.assertIn('{{credit_card_number}}', result)

    @mock.patch.object(Visa, 'get_next_seq_number', mock_get_next_seq_number)
    @httpretty.activate
    @log_capture(level=logging.INFO)
    def test_create_cards(self, l):
        self.spreedly_route()
        self.hermes_status_route()
        self.visa.create_cards(self.card_info_add)
        message = 'Visa batch successful'
        self.assertTrue(any(message in r.msg for r in l.records))

    @mock.patch.object(Visa, 'get_next_seq_number', mock_get_next_seq_number)
    def test_request_body_json(self):
        result, file_name = self.visa.request_body(card_info_reduce)
        self.assertIn('111111111111112', result)
        self.assertIn('{{#gpg}}', result)
        self.assertIn('{{credit_card_number}}', result)
        self.assertGreater(len(file_name), 0)

    def test_set_termination_date(self):
        D = 'D'
        result = self.visa.set_termination_date(D)
        self.assertIsInstance(result, str)
        result = self.visa.set_termination_date('blah')
        self.assertEqual(result, '')

    def test_format_datetime(self):
        date = '2016-10-06T09:50:59.980309Z'
        arrow_date = arrow.get(date)
        result = self.visa.format_datetime(arrow_date)
        self.assertEqual(result, '20161006')

    def test_set_header(self):
        self.vcf.set_header(self.header)
        start_str = '{{#format_text}}%-1000.1000s,'
        end_str = '{{/format_text}}'
        self.assertEqual(start_str, self.vcf.header_string[:29])
        self.assertEqual(end_str, self.vcf.header_string[-16:])

    def test_set_footer(self):
        self.vcf.set_footer(self.footer)
        start_str = '{{#format_text}}%-1000.1000s,'
        end_str = '{{/format_text}}\\n'
        self.assertEqual(start_str, self.vcf.footer_string[:29])
        self.assertEqual(end_str, self.vcf.footer_string[-18:])

    def test_add_detail_start(self):
        self.vcf.details = []
        start_str = '{{#payment_methods}}'
        self.vcf.add_detail_start()
        self.assertEqual(start_str, self.vcf.details[0]['detail'])

    def test_add_detail_end(self):
        self.vcf.details = []
        end_str = '{{/payment_methods}}'
        self.vcf.add_detail_end()
        self.assertEqual(end_str, self.vcf.details[0]['detail'])

    def test_freeze(self):
        self.vcf.details = []
        self.vcf.add_detail_start()
        self.vcf.add_detail_end()
        self.vcf.freeze()
        self.assertGreater(len(self.vcf.details), 0)
