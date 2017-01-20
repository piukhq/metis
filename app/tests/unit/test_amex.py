from unittest import TestCase

# We need the testing flag to be set before we import anything that uses it.
# Unfortunately flake8 doesn't like module-level imports not being at the top of the file, so we `noqa` it.
import os
os.environ['METIS_TESTING'] = 'True'
from app.agents.amex import Amex, mac_auth_header  # noqa


class TestAmex(TestCase):
    def setUp(self):
        self.amex = Amex()

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
        result = mac_auth_header()
        self.assertIn('MAC id', result)
