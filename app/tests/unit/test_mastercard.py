import settings
import app.agents.mastercard as agent
from unittest import TestCase


class Testing:
    TESTING = True


class TestMastercard(TestCase):
    def setUp(self):
        self.mc = agent.MasterCard()

    def test_hostname_testing(self):
        settings.TESTING = True
        result = self.mc.hostname()
        self.assertTrue(result == 'http://latestserver.com/post.php')

    def test_hostname_production(self):
        settings.TESTING = False
        result = self.mc.hostname()
        self.assertTrue(result == '')

    def test_receiver_token_testing(self):
        settings.TESTING = True
        result = self.mc.receiver_token()
        self.assertTrue(result == 'aDwu4ykovZVe7Gpto3rHkYWI5wI')

    def test_receiver_token_production(self):
        settings.TESTING = False
        result = self.mc.receiver_token()
        self.assertTrue(result == '')

    def test_request_header_testing(self):
        settings.TESTING = True
        result = self.mc.request_header()
        self.assertTrue(result.__contains__('mtf'))

    def test_request_header_production(self):
        settings.TESTING = False
        result = self.mc.request_header()
        self.assertFalse(result.__contains__('mtf'))

    def test_request_body_correct_text(self):
        result = self.mc.request_body()
        self.assertTrue(result.__contains__('{{credit_card_number}}'))
        self.assertTrue(result.__contains__('<cus:MEMBER_ICA>17597</cus:MEMBER_ICA>'))
