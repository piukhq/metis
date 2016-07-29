import settings
import app.agents.visa as agent
from unittest import TestCase


class Testing:
    TESTING = True


class TestVisa(TestCase):
    def setUp(self):
        self.visa = agent.Visa()

    def test_url_testing(self):
        settings.TESTING = True
        result = self.visa.url()
        self.assertIn('test.api.loyaltyangels.com', result)

    def test_url_production(self):
        settings.TESTING = False
        result = self.visa.url()
        self.assertIn('test.api.loyaltyangels.com', result)

    def test_receiver_token_testing(self):
        settings.TESTING = True
        result = self.visa.receiver_token()
        self.assertTrue(result == 'aDwu4ykovZVe7Gpto3rHkYWI5wI')

    def test_receiver_token_production(self):
        settings.TESTING = False
        result = self.visa.receiver_token()
        self.assertTrue(result == '')

    def test_request_header_both(self):
        result = self.visa.request_header()
        self.assertIn('json', result)

    def test_request_body_correct_text(self):
        result = self.visa.request_body('123456789')
        self.assertIn('{{credit_card_number}}', result)
        self.assertIn('cmAlias1', result)

    def test_create_file_data(self):
        cards = [1234, 5678, 9876]
        result = self.visa.create_file_data(cards)
        self.assertIn('1234', result)
        self.assertIn('{{credit_card_number}}', result)
