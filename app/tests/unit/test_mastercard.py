from unittest import TestCase

# We need the testing flag to be set before we import anything that uses it.
# Unfortunately flake8 doesn't like module-level imports not being at the top of the file, so we `noqa` it.
import os
os.environ['METIS_TESTING'] = 'True'
from app.agents.mastercard import MasterCard


class TestMastercard(TestCase):
    def setUp(self):
        self.mc = MasterCard()

    def test_url_testing(self):
        result = self.mc.add_url()
        self.assertEqual('http://latestserver.com/post.php', result)

    def test_request_header_testing(self):
        result = self.mc.request_header()
        self.assertIn('xml', result)

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
        self.assertEqual('GF+NsyJx/iX1Yab8k4suJkMG7DBO2lGAB9F2SCY4GWk=', result)

    def test_add_card_soap_template(self):
        card_info = {
            'payment_token': '1111111111111111111111',
            'card_token': '111111111111112',
            'partner_slug': 'mastercard'
        }
        result = self.mc.add_card_soap_template(card_info)
        self.assertIn('loyaltyangels', result)
