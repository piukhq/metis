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
        self.assertTrue(result == 'aDwu4ykovZVe7Gpto3rHkYWI5wI')

    def test_receiver_token_production(self):
        settings.TESTING = False
        result = self.amex.receiver_token()
        self.assertTrue(result == '')

    def test_request_header_both(self):
        result = self.amex.request_header()
        self.assertIn('json', result)

    def test_request_body_correct_text(self):
        result = self.amex.request_body()
        self.assertIn('{{credit_card_number}}', result)
        self.assertIn('cmAlias1', result)
