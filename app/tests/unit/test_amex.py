import app.agents.amex
import settings
import app.agents.amex as agent
from unittest import TestCase


class Testing:
    TESTING = True


class TestAmex(TestCase):
    def setUp(self):
        self.amex = agent.Amex()

    def test_url_testing(self):
        settings.TESTING = True
        result = self.amex.add_url()
        self.assertTrue(result == 'https://api.qa.americanexpress.com/v3/smartoffers/sync')

    def _test_url_production(self):
        settings.TESTING = False
        result = self.amex.url()
        self.assertTrue(result == 'https://api.qa.americanexpress.com/v3/smartoffers/sync')

    def test_receiver_token_testing(self):
        settings.TESTING = True
        result = self.amex.receiver_token()
        self.assertIn('BqfFb1WnOwpbzH7WVTqmvYtffPV', result)

    def test_receiver_token_production(self):
        settings.TESTING = False
        result = self.amex.receiver_token()
        self.assertIn('ZQLPEvBP4jaaYhxHDl7SWobMXDt', result)

    def test_request_header_both(self):
        res_path = "/v3/smartoffers/sync"
        result = self.amex.request_header(res_path)
        self.assertIn('X-AMEX-ACCESS-KEY', result)

    def test_request_body_correct_text(self):
        card_info = {'partner_slug': 'amex',
                     'payment_token': '3ERtq3pUV5OiNpdTCuhhXLBmnv8',
                     'card_token': ''}
        result = self.amex.add_card_request_body(card_info)
        self.assertIn('{{credit_card_number}}', result)
        self.assertIn('cmAlias1', result)

    def test_mac_auth_header(self):
        result = app.agents.amex.mac_auth_header()
        self.assertIn('MAC id', result)

    def test_amex_oauth(self):
        auth_header = app.agents.amex.mac_auth_header()
        result = self.amex.amex_oauth(auth_header)
        self.assertTrue(len(result) > 0)
