import json
from unittest.mock import patch

from flask_testing import TestCase

from metis import create_app, settings

auth_key = (
    "Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL"
    "CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU"
)


class Testing:
    TESTING = True


class TestMetisResources(TestCase):
    def create_app(self):
        return create_app(Testing)

    def test_create_receiver(self):
        resp = self.client.post(
            "/payment_service/create_receiver",
            headers={"content-type": "application/json"},
            data=json.dumps({"receiver_type": "test", "hostname": "http://latestserver.com"}),
        )
        self.assertTrue(resp.status_code == 201)

    def test_create_receiver_invalid_hostname(self):
        resp = self.client.post(
            "/payment_service/create_receiver",
            headers={"content-type": "application/json"},
            data=json.dumps({"hostname": "testing"}),
        )
        self.assertTrue(resp.status_code == 422)

    def test_create_amex_receiver(self):
        resp = self.client.post(
            "/payment_service/create_receiver",
            headers={"content-type": "application/json"},
            data=json.dumps({"receiver_type": "american_express"}),
        )
        self.assertTrue(resp.status_code == 201)

    @patch("metis.auth.parse_token")
    def test_amex_register(self, mock_parse_token):
        settings.TESTING = False
        mock_parse_token.return_value = "{'sub':'45'}"

        resp = self.client.post(
            "/payment_service/payment_card",
            headers={"content-type": "application/json", "Authorization": auth_key},
            data=json.dumps({"partner_slug": "amex", "payment_token": "3ERtq3pUV5OiNpdTCuhhXLBmnv8", "card_token": ""}),
        )
        self.assertTrue(resp.status_code == 200)

    def test_amex_register_auth(self):
        settings.TESTING = False

        resp = self.client.post(
            "/payment_service/payment_card",
            headers={"content-type": "application/json", "Authorization": auth_key},
            data=json.dumps({"partner_slug": "amex", "payment_token": "3ERtq3pUV5OiNpdTCuhhXLBmnv8", "card_token": ""}),
        )
        self.assertTrue(resp.status_code == 200)

    def test_amex_receiver_auth_401(self):
        settings.TESTING = False
        resp = self.client.post(
            "/payment_service/payment_card",
            headers={"content-type": "application/json"},
            data=json.dumps({"partner_slug": "amex", "payment_token": "3ERtq3pUV5OiNpdTCuhhXLBmnv8"}),
        )
        self.assertTrue(resp.status_code == 401)

    @patch("metis.auth.parse_token")
    def test_amex_remove_card(self, mock_parse_token):
        settings.TESTING = False
        mock_parse_token.return_value = "{'sub':'45'}"

        resp = self.client.delete(
            "/payment_service/payment_card",
            headers={"content-type": "application/json", "Authorization": auth_key},
            data=json.dumps({"partner_slug": "amex", "payment_token": "3ERtq3pUV5OiNpdTCuhhXLBmnv8", "card_token": ""}),
        )
        self.assertTrue(resp.status_code == 200)

    @patch("metis.auth.parse_token")
    def test_visa_receiver(self, mock_parse_token):
        card_info = {
            "payment_token": "LyWyubSnJzQZtAxLvN8RYOYnSKv",
            "card_token": "111111111111111111111111",
            "partner_slug": "visa",
        }
        settings.TESTING = False
        mock_parse_token.return_value = "{'sub':'45'}"

        resp = self.client.post(
            "/payment_service/payment_card",
            headers={"content-type": "application/json", "Authorization": auth_key},
            data=json.dumps(card_info),
        )
        self.assertTrue(resp.status_code == 200)

    @patch("metis.auth.parse_token")
    def test_mastercard_enroll(self, mock_parse_token):
        card_info = {"payment_token": "WhtIyJrcpcLupNpBD4bSVx3qyY5", "card_token": " ", "partner_slug": "mastercard"}
        settings.TESTING = False
        mock_parse_token.return_value = "{'sub':'45'}"

        resp = self.client.post(
            "/payment_service/payment_card",
            headers={"content-type": "application/json", "Authorization": auth_key},
            data=json.dumps(card_info),
        )
        self.assertTrue(resp.status_code == 200)

    @patch("metis.auth.parse_token")
    def test_mastercard_unenroll(self, mock_parse_token):
        card_info = {"payment_token": "RjG4WgzYoBZWgJ1ZK3KsHd2nYRv", "card_token": " ", "partner_slug": "mastercard"}
        settings.TESTING = False
        mock_parse_token.return_value = "{'sub':'45'}"

        resp = self.client.post(
            "/payment_service/remove_card",
            headers={"content-type": "application/json", "Authorization": auth_key},
            data=json.dumps(card_info),
        )
        self.assertTrue(resp.status_code == 200)
