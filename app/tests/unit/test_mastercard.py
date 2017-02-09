import os
from unittest import TestCase
import jinja2

os.environ['METIS_TESTING'] = 'True'
import app.agents.mastercard as mastercard  # noqa


class TestMastercard(TestCase):
    def setUp(self):
        self.card_info = {
            'payment_token': '1111111111111111111111',
            'card_token': '111111111111112',
            'partner_slug': 'mastercard'
        }
        self.mc = mastercard.MasterCard()

    def test_url_testing(self):
        result = self.mc.add_url()
        self.assertEqual('http://latestserver.com/post.php', result)

        result = self.mc.remove_url()
        self.assertEqual('http://latestserver.com/post.php', result)

    def test_receiver_token(self):
        token = 'XsXRs91pxREDW7TAFbUc1TgosxU/deliver.xml'
        result = self.mc.receiver_token()
        self.assertEqual(token, result)

    def test_request_header_testing(self):
        result = self.mc.request_header()
        self.assertIn('xml', result)

    def test_add_card_body(self):
        result = self.mc.add_card_body(self.card_info)
        self.assertIn('payment_method_token', result)
        self.assertIn('url', result)
        self.assertIn('headers', result)
        self.assertIn('body', result)

    def test_request_body_correct_text(self):
        result = self.mc.add_card_request_body(self.card_info)
        self.assertIn('Envelope', result)
        # self.assertIn('{{credit_card_number}}', result)
        # self.assertIn('<cus:MEMBER_ICA>17597</cus:MEMBER_ICA>', result)

    def test_remove_card_body(self):
        result = self.mc.remove_card_body(self.card_info)
        self.assertIn('<payment_method_token>1111111111111111111111</payment_method_token>', result)

    def test_do_echo_body(self):
        result = self.mc.do_echo_body(self.card_info)
        self.assertIn(mastercard.MASTERCARD_DO_ECHO_URL, result)
        self.assertIn('payment_method_token', result)
        self.assertIn('url', result)
        self.assertIn('headers', result)
        self.assertIn('body', result)

    # We are not hashing anymore.
    def _test_get_hash(self):
        result = self.mc.get_hash('Hello')
        self.assertEqual('GF+NsyJx/iX1Yab8k4suJkMG7DBO2lGAB9F2SCY4GWk=', result)

    def test_add_card_soap_template(self):
        card_info = {
            'payment_token': '1111111111111111111111',
            'card_token': '111111111111112',
            'partner_slug': 'mastercard'
        }
        result = self.mc.add_card_soap_template(card_info)
        self.assertIn('loyaltyangels', result)

    def test_jinja_environment(self):
        result = self.mc.jinja_environment()
        self.assertIsInstance(result, jinja2.environment.Environment)
