import os
from importlib import reload
from unittest import TestCase

import app.agents.amex as amex

os.environ['METIS_TESTING'] = 'True'
reload(amex.settings)


class TestAmex(TestCase):
    def setUp(self):
        self.amex = amex.Amex()

    def test_url_testing(self):
        result = self.amex.add_url()
        self.assertEqual('https://api.qa.americanexpress.com/v3/smartoffers/sync', result)

    def test_receiver_token_testing(self):
        result = self.amex.receiver_token()
        self.assertIn('BqfFb1WnOwpbzH7WVTqmvYtffPV', result)

    def test_request_body_correct_text(self):
        card_info = {'partner_slug': 'amex',
                     'payment_token': '3ERtq3pUV5OiNpdTCuhhXLBmnv8',
                     'card_token': ''}
        result = self.amex.add_card_request_body(card_info)
        self.assertIn('{{credit_card_number}}', result)
        self.assertIn('cmAlias1', result)

    def test_mac_auth_header(self):
        result = amex.mac_auth_header()
        self.assertIn('MAC id', result)
