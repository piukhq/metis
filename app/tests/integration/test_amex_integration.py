import unittest
from unittest.mock import patch

import app.services
import settings
from app.agents.amex import Amex


class TestServices(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        settings.TESTING = True
        settings.STUBBED_AMEX_URL = "https://api.dev2s.americanexpress.com"
        settings.AZURE_VAULT_URL = "http://127.0.0.1:8200"
        settings.secrets_from_vault(start_delay=0)

    def setUp(self):
        self.token = 'QdjGCPSiYYDKxPMvvluYRG6zq79'

    @patch("app.services.put_account_status", autospec=True)
    @patch("app.services.get_provider_status_mappings", autospec=True)
    def test_amex_sync(self, status_map_mock, status_return_mock):
        card_info = {
            'payment_token': self.token,
            'card_token': ' ',
            'partner_slug': 'amex',
            'id': 100
        }
        status_map_mock.return_value = {"BINK_UNKNOWN": 0}
        resp = app.services.add_card(card_info)
        self.assertTrue(resp["status_code"] == 200)
        self.assertDictEqual(status_return_mock.call_args[1], {
            'card_id': 100, 'response_action': 'Add', 'response_status_code': 200,
            'response_message': f'Amex Add successful - Token: {self.token}, Amex successfully processed'
        })

    @patch("app.services.get_provider_status_mappings", autospec=True)
    def test_amex_unsync(self, status_map_mock):
        card_info = {
            'payment_token': self.token,
            'card_token': ' ',
            'partner_slug': 'amex',
            'id': 100
        }
        status_map_mock.return_value = {"BINK_UNKNOWN": 0}
        resp = app.services.remove_card(card_info)
        self.assertTrue(resp["status_code"] == 200)

    def test_request_header_both(self):
        res_path = "/v3/smartoffers/sync"
        amex = Amex()
        req_body = ""
        result = amex.request_header(res_path, req_body)
        self.assertIn(f'Authorization: "MAC id="{settings.Secrets.amex_client_id}"', result)
        self.assertIn(f'X-AMEX-API-KEY: {settings.Secrets.amex_client_id}]]>', result)
