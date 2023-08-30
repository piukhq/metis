import json
from unittest.mock import patch

import httpretty
from flask_testing import TestCase

import metis.agents.mastercard as mc
from metis import create_app, settings
from metis.action import ActionCode

auth_key = (
    "Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL"
    "CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU"
)


class Testing:
    TESTING = True


class TestMetisResources(TestCase):
    xml_response = "<receiver>" "<receiver_type>test1</receiver_type>" "</receiver>"

    receiver_token = "testing_624624613fgae3"

    def create_app(self):
        return create_app(Testing)

    def create_receiver_route(self):
        url = "https://core.spreedly.com/v1/receivers.xml"
        httpretty.register_uri(httpretty.POST, url, status=201, body=self.xml_response, content_type="application/xml")

    def end_site_receiver_route(self):
        url = "https://core.spreedly.com/v1/receivers/" + self.receiver_token + "/deliver.xml"
        httpretty.register_uri(httpretty.POST, url, status=200, body=self.xml_response, content_type="application/xml")

    def retain_route(self):
        url = "https://core.spreedly.com/v1/payment_methods/1111111111111111111111/retain.json"
        httpretty.register_uri(httpretty.PUT, url, status=200, content_type="application/json")

    @patch("metis.auth.parse_token")
    @httpretty.activate
    def test_create_receiver(self, mock_parse_token):
        mock_parse_token.return_value = "{'sub':''45'}"
        self.create_receiver_route()
        resp = self.client.post(
            "/payment_service/create_receiver",
            headers={"content-type": "application/json", "Authorization": auth_key},
            data=json.dumps({"receiver_type": "test"}),
        )
        self.assertTrue(resp.status_code == 201)

    @patch("metis.auth.parse_token")
    @httpretty.activate
    def test_create_receiver_invalid_hostname(self, mock_parse_token):
        mock_parse_token.return_value = "{'sub':''45'}"
        self.create_receiver_route()
        resp = self.client.post(
            "/payment_service/create_receiver",
            headers={"content-type": "application/json", "Authorization": auth_key},
            data=json.dumps({}),
        )
        self.assertTrue(resp.status_code == 422)

    @patch("metis.resources.process_card")
    @patch("metis.auth.parse_token")
    @httpretty.activate
    def test_end_site_receiver(self, mock_parse_token, mock_process_card):
        test_card = {
            "id": 1,
            "payment_token": "1111111111111111111111",
            "card_token": "1111111111111111111111",
            "partner_slug": "mastercard",
            "date": 1475920002,
        }
        settings.TESTING = True
        mock_parse_token.return_value = "{'sub':''45'}"
        mc.testing_receiver_token = self.receiver_token
        self.retain_route()
        self.end_site_receiver_route()
        resp = self.client.post(
            "/payment_service/payment_card",
            headers={"content-type": "application/json", "Authorization": auth_key, "X-Azure-Ref": "azure-ref"},
            data=json.dumps(test_card),
        )
        self.assertEqual(resp.status_code, 200)
        mock_process_card.assert_called_with(ActionCode.ADD, test_card, x_azure_ref="azure-ref")

    @patch("metis.auth.parse_token")
    @httpretty.activate
    def test_end_site_receiver_invalid_param(self, mock_parse_token):
        mock_parse_token.return_value = "{'sub':''45'}"
        self.end_site_receiver_route()
        self.retain_route()
        resp = self.client.post(
            "/payment_service/payment_card",
            headers={"content-type": "application/json", "Authorization": auth_key},
            data=json.dumps({}),
        )
        self.assertEqual(resp.status_code, 400)

    @patch("metis.auth.parse_token")
    @httpretty.activate
    def test_end_site_receiver_param_missing(self, mock_parse_token):
        mock_parse_token.return_value = "{'sub':''45'}"
        self.end_site_receiver_route()
        self.retain_route()
        resp = self.client.post(
            "/payment_service/payment_card",
            headers={"content-type": "application/json", "Authorization": auth_key},
            data=json.dumps({"partner_slug": "mastercard"}),
        )
        self.assertTrue(resp.status_code == 400)

    @patch("metis.auth.parse_token")
    @httpretty.activate
    def test_end_site_blank_param(self, mock_parse_token):
        test_card = {
            "id": 1,
            "payment_token": "",
            "card_token": "1111111111111111111111",
            "partner_slug": "visa",
            "date": 1475920002,
        }
        mock_parse_token.return_value = "{'sub':''45'}"
        self.end_site_receiver_route()
        self.retain_route()
        resp = self.client.post(
            "/payment_service/payment_card",
            headers={"content-type": "application/json", "Authorization": auth_key},
            data=json.dumps(test_card),
        )
        self.assertTrue(resp.status_code == 400)
