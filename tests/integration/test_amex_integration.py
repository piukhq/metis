import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

import responses

import metis.services
from metis.agents.amex import Amex
from metis.settings import settings
from metis.vault import Secrets


class TestServicesToAmexMock(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        settings.METIS_TESTING = True
        settings.STUBBED_AMEX_URL = "http://127.0.0.1:5050"
        settings.AZURE_VAULT_URL = ""

    def setUp(self) -> None:
        self.token = "QdjGCPSiYYDKxPMvvluYRG6zq79"

    @responses.activate
    @patch("metis.services.put_account_status", autospec=True)
    @patch("metis.services.get_provider_status_mappings", autospec=True)
    def test_amex_sync_fail(self, status_map_mock: Mock, status_return_mock: Mock) -> None:
        token = f"REQADD_XXXXXX_1_1_1_{uuid4()}"
        card_info = {"payment_token": token, "card_token": " ", "partner_slug": "amex", "id": 100}
        status_map_mock.return_value = {"BINK_UNKNOWN": 0}
        responses.add(
            responses.POST,
            "https://core.spreedly.com/v1/receivers/amex/deliver.xml",
            body="""
            <root>
                <status>Failure</status>
                <payment_method>
                    <token>QdjGCPSiYYDKxPMvvluYRG6zq79</token>
                </payment_method>
                <body>{"respCd": "XXXXXX", "respDesc": "Failure", "status": "Failure"}</body>
            </root>
            """,
            content_type="application/xml",
        )
        assert (resp := metis.services.add_card(card_info))
        self.assertTrue(resp["status_code"] == 422)
        self.assertDictEqual(
            status_return_mock.call_args[1],
            {
                "card_id": 100,
                "response_action": "Add",
                "response_status_code": 422,
                "response_message": "Add Amex fault recorded. Code: XXXXXX",
            },
        )

    @responses.activate
    @patch("metis.services.put_account_status", autospec=True)
    @patch("metis.services.get_provider_status_mappings", autospec=True)
    def test_amex_sync(self, status_map_mock: Mock, status_return_mock: Mock) -> None:
        card_info = {"payment_token": self.token, "card_token": " ", "partner_slug": "amex", "id": 100}
        status_map_mock.return_value = {"BINK_UNKNOWN": 0}
        responses.add(
            responses.POST,
            "https://core.spreedly.com/v1/receivers/amex/deliver.xml",
            body="""
            <root>
                <status>Success</status>
                <payment_method>
                    <token>QdjGCPSiYYDKxPMvvluYRG6zq79</token>
                </payment_method>
                <body>{"respCd": "200", "respDesc": "Success", "status": "Processed"}</body>
            </root>
            """,
            content_type="application/xml",
        )
        assert (resp := metis.services.add_card(card_info))
        self.assertTrue(resp["status_code"] == 200)
        self.assertDictEqual(
            status_return_mock.call_args[1],
            {
                "card_id": 100,
                "response_action": "Add",
                "response_status_code": 200,
                "response_message": f"Amex Add successful - Token: {self.token}, Amex successfully processed",
            },
        )

    @responses.activate
    @patch("metis.services.get_provider_status_mappings", autospec=True)
    def test_amex_unsync(self, status_map_mock: Mock) -> None:
        card_info = {"payment_token": self.token, "card_token": " ", "partner_slug": "amex", "id": 100}
        status_map_mock.return_value = {"BINK_UNKNOWN": 0}
        responses.add(
            responses.POST,
            "https://core.spreedly.com/v1/receivers/amex/deliver.xml",
            body="""
            <root>
                <status>Success</status>
                <payment_method>
                    <token>QdjGCPSiYYDKxPMvvluYRG6zq79</token>
                </payment_method>
                <body>{"respCd": "200", "respDesc": "Success", "status": "Processed"}</body>
            </root>
            """,
            content_type="application/xml",
        )
        resp = metis.services.remove_card(card_info)
        assert (resp := metis.services.remove_card(card_info))
        self.assertTrue(resp["status_code"] == 200)

    @responses.activate
    def test_request_header_both(self) -> None:
        res_path = "/v3/smartoffers/sync"
        amex = Amex()
        req_body = ""
        result = amex.request_header(res_path, req_body)
        self.assertIn(f'Authorization: "MAC id="{Secrets.amex_client_id}"', result)
        self.assertIn(f"X-AMEX-API-KEY: {Secrets.amex_client_id}]]>", result)
