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
        result = self.amex.url()
        self.assertTrue(result == 'https://api.qa.americanexpress.com/v2/datapartnership/offers/sync')

    def test_url_production(self):
        settings.TESTING = False
        result = self.amex.url()
        self.assertTrue(result == 'https://apigateway.americanexpress.com/v2/datapartnership/offers/sync')

    def test_receiver_token_testing(self):
        settings.TESTING = True
        result = self.amex.receiver_token()
        self.assertTrue(result == 'BqfFb1WnOwpbzH7WVTqmvYtffPV')

    def test_receiver_token_production(self):
        settings.TESTING = False
        result = self.amex.receiver_token()
        self.assertTrue(result == '')

    def test_request_header_both(self):
        result = self.amex.request_header()
        self.assertIn('X-AMEX-ACCESS-KEY', result)

    def test_request_body_correct_text(self):
        result = self.amex.request_body()
        self.assertIn('{{credit_card_number}}', result)
        self.assertIn('cmAlias1', result)

    def test_mac_auth_header(self):
        result = app.agents.amex.mac_auth_header()
        self.assertIn('MAC id', result)

    def test_amex_oauth(self):
        auth_header = app.agents.amex.mac_auth_header()
        result = self.amex.amex_oauth(auth_header)
        self.assertTrue(len(result) > 0)
