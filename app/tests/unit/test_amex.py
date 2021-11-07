import json
from unittest import TestCase

import app.agents.amex as amex
import settings


class TestAmex(TestCase):
    def setUp(self):
        settings.TESTING = True
        self.amex = amex.Amex()

        self.card_info = {"partner_slug": "amex", "payment_token": "3ERtq3pUV5OiNpdTCuhhXLBmnv8", "card_token": ""}

        self.add_card_req_body = self.amex.add_card_body(self.card_info)

    def tearDown(self):
        settings.TESTING = False

    def test_request_header(self):
        result = self.amex.request_header(amex.res_path_sync, self.add_card_req_body)
        self.assertIn(result[:6], "<![CDATA[")
        self.assertIn(result[9:39], "Content-Type: application/json")
        self.assertIn(result[40:55], "Authorization: ")
        self.assertIn(f"X-AMEX-API-KEY: {self.amex.client_id}", result)

    def test_remove_card_request_body(self):
        result = self.amex.remove_card_request_body(self.card_info)
        j = json.loads(result[9:-3])
        self.assertIn("msgId", j.keys())
        self.assertIn("partnerId", j.keys())
        self.assertIn("cmAlias1", j.keys())
        self.assertIn("distrChan", j.keys())

    def test_request_body_correct_text(self):
        result = self.amex.add_card_request_body(self.card_info)
        self.assertIn("{{credit_card_number}}", result)
        self.assertIn("cmAlias1", result)

    def test_add_card_body(self):
        result = self.amex.add_card_body(self.card_info)
        self.assertIn("<delivery>", result)
        self.assertIn("<payment_method_token>", result)
        self.assertIn("<url>", result)
        self.assertIn("<headers>", result)
        self.assertIn("<body>", result)

    def test_remove_card_body(self):
        result = self.amex.remove_card_body(self.card_info)
        self.assertIn("<delivery>", result)
        self.assertIn("<payment_method_token>", result)
        self.assertIn("<url>", result)
        self.assertIn("<headers>", result)
        self.assertIn("<body>", result)
