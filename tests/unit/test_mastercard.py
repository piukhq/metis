from unittest import TestCase

import jinja2

from metis.agents import mastercard
from metis.settings import settings


class TestMastercard(TestCase):
    def setUp(self) -> None:
        self.card_info = {
            "payment_token": "1111111111111111111111",
            "card_token": "111111111111112",
            "partner_slug": "mastercard",
        }
        self.mc = mastercard.MasterCard()
        settings.METIS_TESTING = True

    def tearDown(self) -> None:
        settings.METIS_TESTING = False

    def test_request_header_testing(self) -> None:
        result = self.mc.xml_header
        self.assertIn("xml", result)

    def test_add_card_body(self) -> None:
        result = self.mc.add_card_body(self.card_info)
        self.assertIn("payment_method_token", result)
        self.assertIn("url", result)
        self.assertIn("headers", result)
        self.assertIn("body", result)

    def test_request_body_correct_text(self) -> None:
        result = self.mc.add_card_request_body(self.card_info)
        self.assertIn("Envelope", result)

    def test_remove_card_body(self) -> None:
        result = self.mc.remove_card_body(self.card_info)
        self.assertIn("<payment_method_token>1111111111111111111111</payment_method_token>", result)

    def test_do_echo_body(self) -> None:
        result = self.mc.do_echo_body(self.card_info)
        self.assertIn(mastercard.MASTERCARD_DO_ECHO_URL, result)
        self.assertIn("payment_method_token", result)
        self.assertIn("url", result)
        self.assertIn("headers", result)
        self.assertIn("body", result)

    def test_add_card_soap_template(self) -> None:
        card_info = {
            "payment_token": "1111111111111111111111",
            "card_token": "111111111111112",
            "partner_slug": "mastercard",
        }
        result = self.mc.add_card_soap_template(card_info)
        self.assertIn("loyaltyangels", result)

    def test_jinja_environment(self) -> None:
        result = self.mc.jinja_environment()
        self.assertIsInstance(result, jinja2.environment.Environment)
