import unittest
import settings
from app.services import add_card, remove_card


class TestServices(unittest.TestCase):

    def test_amex_sync(self):
        card_info = {
            'payment_token': '3ERtq3pUV5OiNpdTCuhhXLBmnv8',
            'card_token': ' ',
            'partner_slug': 'amex'
        }
        settings.TESTING = False

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
