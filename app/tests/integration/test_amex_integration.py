import unittest
from unittest.mock import patch
from uuid import uuid4

import app.services
import settings
from app.agents.amex import Amex


class TestServicesToAmexDev2s(unittest.TestCase):
    """
    To run this test you must have port forward to dev vault using:
        kubectl port-forward svc/fakicorp 8200

    Tests must run in correct order since sync will error on a already sync card and visa vers for unsync
    """

    @classmethod
    def setUpClass(cls):
        settings.TESTING = True
        settings.STUBBED_AMEX_URL = "https://api.dev2s.americanexpress.com"
        settings.AZURE_VAULT_URL = "https://bink-uksouth-dev-com.vault.azure.net/"
        settings.secrets_from_vault(start_delay=0)

    def setUp(self):
        self.token = "QdjGCPSiYYDKxPMvvluYRG6zq79"

    @patch("app.services.put_account_status", autospec=True)
    @patch("app.services.get_provider_status_mappings", autospec=True)
    def test_amex_sync(self, status_map_mock, status_return_mock):
        card_info = {"payment_token": self.token, "card_token": " ", "partner_slug": "amex", "id": 100}
        status_map_mock.return_value = {"BINK_UNKNOWN": 0}
        resp = app.services.add_card(card_info)
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

    @patch("app.services.get_provider_status_mappings", autospec=True)
    def test_amex_unsync(self, status_map_mock):
        card_info = {"payment_token": self.token, "card_token": " ", "partner_slug": "amex", "id": 100}
        status_map_mock.return_value = {"BINK_UNKNOWN": 0}
        resp = app.services.remove_card(card_info)
        self.assertTrue(resp["status_code"] == 200)

    def test_request_header_both(self):
        res_path = "/v3/smartoffers/sync"
        amex = Amex()
        req_body = ""
        result = amex.request_header(res_path, req_body)
        self.assertIn(f'Authorization: "MAC id="{settings.Secrets.amex_client_id}"', result)
        self.assertIn(f"X-AMEX-API-KEY: {settings.Secrets.amex_client_id}]]>", result)


class TestServicesToPelopsAmexMock(unittest.TestCase):
    """
    To run this test you must have a local Pelops Copy running on local host 5050

    """

    @classmethod
    def setUpClass(cls):
        settings.TESTING = True
        settings.SPREEDLY_BASE_URL = "http://127.0.01:5050/spreedly"
        settings.STUBBED_AMEX_URL = "http://127.0.0.1:5050"
        settings.AZURE_VAULT_URL = ""

    def setUp(self):
        self.token = "QdjGCPSiYYDKxPMvvluYRG6zq79"

    @patch("app.services.put_account_status", autospec=True)
    @patch("app.services.get_provider_status_mappings", autospec=True)
    def test_amex_sync_fail(self, status_map_mock, status_return_mock):
        token = f"REQADD_XXXXXX_1_1_1_{uuid4()}"
        card_info = {"payment_token": token, "card_token": " ", "partner_slug": "amex", "id": 100}
        status_map_mock.return_value = {"BINK_UNKNOWN": 0}
        resp = app.services.add_card(card_info)
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

    @patch("app.services.put_account_status", autospec=True)
    @patch("app.services.get_provider_status_mappings", autospec=True)
    def test_amex_sync(self, status_map_mock, status_return_mock):
        card_info = {"payment_token": self.token, "card_token": " ", "partner_slug": "amex", "id": 100}
        status_map_mock.return_value = {"BINK_UNKNOWN": 0}
        resp = app.services.add_card(card_info)
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

    @patch("app.services.get_provider_status_mappings", autospec=True)
    def test_amex_unsync(self, status_map_mock):
        card_info = {"payment_token": self.token, "card_token": " ", "partner_slug": "amex", "id": 100}
        status_map_mock.return_value = {"BINK_UNKNOWN": 0}
        resp = app.services.remove_card(card_info)
        self.assertTrue(resp["status_code"] == 200)

    def test_request_header_both(self):
        res_path = "/v3/smartoffers/sync"
        amex = Amex()
        req_body = ""
        result = amex.request_header(res_path, req_body)
        self.assertIn(f'Authorization: "MAC id="{settings.Secrets.amex_client_id}"', result)
        self.assertIn(f"X-AMEX-API-KEY: {settings.Secrets.amex_client_id}]]>", result)
