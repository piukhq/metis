import unittest
import settings
from app.services import add_card, remove_card
from app.agents.amex import Amex


class TestServices(unittest.TestCase):

    def test_amex_sync(self):
        card_info = {
            'payment_token': '3ERtq3pUV5OiNpdTCuhhXLBmnv8',
            'card_token': ' ',
            'partner_slug': 'amex'
        }
        settings.TESTING = False
        self.amex = Amex()

        resp = add_card(card_info)
        self.assertTrue(resp.status_code == 200)

    def test_amex_unsync(self):
        card_info = {
            'payment_token': '3ERtq3pUV5OiNpdTCuhhXLBmnv8',
            'card_token': ' ',
            'partner_slug': 'amex'
        }
        settings.TESTING = False

        resp = remove_card(card_info)
        self.assertTrue(resp.status_code == 200)

    def test_amex_oauth(self):
        settings.TESTING = False
        self.amex = Amex()

        auth_header = self.amex.mac_auth_header()
        result = self.amex.amex_oauth(auth_header)
        self.assertGreater(len(result), 0)

    def test_request_header_both(self):
        res_path = "/v3/smartoffers/sync"
        result = self.amex.request_header(res_path)
        self.assertIn('X-AMEX-ACCESS-KEY', result)
