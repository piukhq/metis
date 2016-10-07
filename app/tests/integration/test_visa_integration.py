import unittest
import settings
from app.services import add_card, remove_card
from unittest.mock import patch


class TestServices(unittest.TestCase):

    @patch('app.agents.visa.sentry')
    def test_visa_add_card(self, mock_sentry):
        card_info = [{
            'payment_token': 'LyWyubSnJzQZtAxLvN8RYOYnSKv',
            'card_token': '1111111111111111111111112',
            'partner_slug': 'visa'
        }]

        settings.TESTING = False

        resp = add_card(card_info)

        self.assertTrue(resp['status_code'] == 202)

    @patch('app.agents.visa.sentry')
    def test_visa_add_card_wrong_token(self, mock_sentry):
        card_info = [{
            'payment_token': 'LyWyubSnJzQZtAxLvN8RYOYnS11',
            'card_token': '1111111111111111111111112',
            'partner_slug': 'visa'
        }]

        settings.TESTING = True

        resp = add_card(card_info)

        mock_sentry.captureMessage.assert_called_with(
            'Problem connecting to PSP. Action: Visa Add. Error:Unable to find the specified receiver.')
        self.assertTrue(resp['status_code'] == 404)

    @patch('app.agents.visa.sentry')
    def test_visa_remove_card(self, mock_sentry):
        card_info = [{
            'payment_token': 'LyWyubSnJzQZtAxLvN8RYOYnSKv',
            'card_token': '1111111111111111111111112',
            'partner_slug': 'visa'
        }]
        settings.TESTING = False

        resp = remove_card(card_info)
        self.assertTrue(resp.status_code == 200)
