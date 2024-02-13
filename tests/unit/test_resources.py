import unittest
from typing import ClassVar
from unittest.mock import Mock, patch

import respx
from fastapi.testclient import TestClient
from httpx import Response

from metis import create_app
from metis.action import ActionCode
from metis.settings import settings

auth_key = (
    "Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL"
    "CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU"
)


class TestMetisResources(unittest.TestCase):
    client: TestClient
    response_xml_headers: ClassVar[dict] = {"Content-Type": "application/xml"}
    response_json_headers: ClassVar[dict] = {"Content-Type": "application/json"}
    xml_response = "<receiver>" "<receiver_type>test1</receiver_type>" "</receiver>"
    receiver_token = "testing_624624613fgae3"

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(create_app(), raise_server_exceptions=False)

    def create_receiver_route(self) -> None:
        url = "https://core.spreedly.com/v1/receivers.xml"
        respx.post(url).mock(
            return_value=Response(status_code=201, text=self.xml_response, headers=self.response_xml_headers)
        )

    def end_site_receiver_route(self) -> None:
        url = "https://core.spreedly.com/v1/receivers/" + self.receiver_token + "/deliver.xml"
        respx.post(url).mock(
            return_value=Response(status_code=200, text=self.xml_response, headers=self.response_xml_headers)
        )

    def retain_route(self) -> None:
        url = "https://core.spreedly.com/v1/payment_methods/1111111111111111111111/retain.json"
        respx.put(url).mock(return_value=Response(status_code=200, headers=self.response_json_headers))

    @patch("metis.api.deps.parse_token")
    @respx.mock
    def test_create_receiver(self, mock_parse_token: Mock) -> None:
        mock_parse_token.return_value = "{'sub':''45'}"
        self.create_receiver_route()
        resp = self.client.post(
            "/payment_service/create_receiver",
            headers={"Authorization": auth_key},
            json={"receiver_type": "test"},
        )
        self.assertTrue(resp.status_code == 201)

    @patch("metis.api.deps.parse_token")
    @respx.mock
    def test_create_receiver_invalid_hostname(self, mock_parse_token: Mock) -> None:
        mock_parse_token.return_value = "{'sub':''45'}"
        self.create_receiver_route()
        resp = self.client.post(
            "/payment_service/create_receiver",
            headers={"Authorization": auth_key},
            json={},
        )
        self.assertTrue(resp.status_code == 422)

    @patch("metis.api.resources.process_card")
    @patch("metis.api.deps.parse_token")
    @respx.mock
    def test_end_site_receiver(self, mock_parse_token: Mock, mock_process_card: Mock) -> None:
        test_card = {
            "id": 1,
            "payment_token": "1111111111111111111111",
            "card_token": "1111111111111111111111",
            "partner_slug": "mastercard",
            "date": 1475920002,
        }
        settings.METIS_TESTING = True
        mock_parse_token.return_value = "{'sub':''45'}"
        self.retain_route()
        self.end_site_receiver_route()

        resp = self.client.post(
            "/payment_service/payment_card",
            headers={"Authorization": auth_key, "X-Azure-Ref": "azure-ref"},
            json=test_card,
        )

        self.assertEqual(resp.status_code, 200)
        mock_process_card.assert_called_with(ActionCode.ADD, test_card, priority=10, x_azure_ref="azure-ref")

    @patch("metis.api.deps.parse_token")
    @respx.mock
    def test_end_site_receiver_invalid_param(self, mock_parse_token: Mock) -> None:
        mock_parse_token.return_value = "{'sub':''45'}"
        self.end_site_receiver_route()
        self.retain_route()
        resp = self.client.post(
            "/payment_service/payment_card",
            headers={"Authorization": auth_key},
            json={},
        )
        self.assertEqual(resp.status_code, 400)

    @patch("metis.api.deps.parse_token")
    @respx.mock
    def test_end_site_receiver_param_missing(self, mock_parse_token: Mock) -> None:
        mock_parse_token.return_value = "{'sub':''45'}"
        self.end_site_receiver_route()
        self.retain_route()
        resp = self.client.post(
            "/payment_service/payment_card",
            headers={"Authorization": auth_key},
            json={"partner_slug": "mastercard"},
        )
        self.assertTrue(resp.status_code == 400)

    @patch("metis.api.deps.parse_token")
    @respx.mock
    def test_end_site_blank_param(self, mock_parse_token: Mock) -> None:
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
            headers={"Authorization": auth_key},
            json=test_card,
        )
        self.assertTrue(resp.status_code == 400)
