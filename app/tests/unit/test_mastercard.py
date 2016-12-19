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
        result = self.mc.add_url()
        self.assertTrue(result == 'http://latestserver.com/post.php')

    def test_url_production(self):
        settings.TESTING = False
        result = self.mc.add_url()
        self.assertIn("CustomerService", result)

    def test_receiver_token_production(self):
        settings.TESTING = False
        result = self.mc.receiver_token()
        self.assertIn('SiXfsuR5TQJ87wjH2O5Mo1I5WR', result)

    def test_request_header_testing(self):
        settings.TESTING = True
        result = self.mc.request_header()
        self.assertIn('xml', result)

    def test_request_header_production(self):
        settings.TESTING = False
        result = self.mc.request_header()
        self.assertNotIn('mtf', result)

    def test_request_body_correct_text(self):
        card_info = {
            'payment_token': '1111111111111111111111',
            'card_token': '111111111111112',
            'partner_slug': 'mastercard'
        }
        result = self.mc.add_card_request_body(card_info)
        self.assertIn('Envelope', result)
        # self.assertIn('{{credit_card_number}}', result)
        # self.assertIn('<cus:MEMBER_ICA>17597</cus:MEMBER_ICA>', result)

    def test_remove_card_request_body(self):
        card_info = {
            'payment_token': '1111111111111111111111',
            'card_token': '111111111111112',
            'partner_slug': 'mastercard'
        }
        result = self.mc.remove_card_body(card_info)
        self.assertIn('<payment_method_token>1111111111111111111111</payment_method_token>', result)

    # We are not hashing anymore.
    def _test_get_hash(self):
        result = self.mc.get_hash('Hello')
        self.assertTrue(result == 'GF+NsyJx/iX1Yab8k4suJkMG7DBO2lGAB9F2SCY4GWk=')

    def test_add_card_soap_template(self):
        card_info = {
            'payment_token': '1111111111111111111111',
            'card_token': '111111111111112',
            'partner_slug': 'mastercard'
        }
        result = self.mc.add_card_soap_template(card_info)
        self.assertIn('loyaltyangels', result)
