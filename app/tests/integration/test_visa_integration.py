import unittest
import settings
from app.services import add_card, remove_card


class TestServices(unittest.TestCase):

    def test_visa_add_card(self):
        card_info = [{
            'payment_token': 'LyWyubSnJzQZtAxLvN8RYOYnSKv',
            'card_token': '1111111111111111111111112',
            'partner_slug': 'visa'
        }]
        settings.TESTING = True

        resp = add_card(card_info)
        self.assertTrue(resp.status_code == 200)

    def test_visa_remove_card(self):
        card_info = [{
            'payment_token': 'LyWyubSnJzQZtAxLvN8RYOYnSKv',
            'card_token': '1111111111111111111111112',
            'partner_slug': 'visa'
        }]
        settings.TESTING = False

        resp = remove_card(card_info)
        self.assertTrue(resp.status_code == 200)
