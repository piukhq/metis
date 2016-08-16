import settings
import app.agents.mastercard as agent
from unittest import TestCase


class Testing:
    TESTING = True


class TestMastercard(TestCase):
    def setUp(self):
        self.mc = agent.MasterCard()

    def test_url_testing(self):
        settings.TESTING = True
        result = self.mc.url()
        self.assertTrue(result == 'http://latestserver.com/post.php')

    def test_url_production(self):
        settings.TESTING = False
        result = self.mc.url()
        self.assertTrue(result == '')

    def test_receiver_token_production(self):
        settings.TESTING = False
        result = self.mc.receiver_token()
        self.assertTrue(result == '')

    def test_request_header_testing(self):
        settings.TESTING = True
        result = self.mc.request_header()
        self.assertIn('mtf', result)

    def test_request_header_production(self):
        settings.TESTING = False
        result = self.mc.request_header()
        self.assertNotIn('mtf', result)

    def test_request_body_correct_text(self):
        result = self.mc.request_body('123456789')
        self.assertIn('{{credit_card_number}}', result)
        self.assertIn('<cus:MEMBER_ICA>17597</cus:MEMBER_ICA>', result)

    def test_get_hash(self):
        result = self.mc.get_hash('Hello')
        self.assertTrue(result == 'GF+NsyJx/iX1Yab8k4suJkMG7DBO2lGAB9F2SCY4GWk=')

    def test_create_soap_request(self):
        result = self.mc.create_soap_template()
        self.assertIn('LoyaltyAngels', result)
        self.assertIn('Hello', result)

    def test_process_soap_xml(self):
        test_xml = self.mc.create_soap_template()
        result = self.mc.process_soap_xml(test_xml)
        self.assertTrue(len(result) > 0)
        # self.assertIn('Hello', result)
