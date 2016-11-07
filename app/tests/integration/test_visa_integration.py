import unittest
import settings
from app.services import add_card, remove_card
from unittest.mock import patch
from app.card_router import ActionCode
from app.agents.visa import Visa
from app.tests.unit.fixture import real_list


class TestServices(unittest.TestCase):

    @patch('app.agents.visa.sentry')
    def test_visa_add_card(self, mock_sentry):
        card_info = {
            'payment_token': 'LyWyubSnJzQZtAxLvN8RYOYnSKv',
            'card_token': '1111111111111111111111112',
            'partner_slug': 'visa'
        }

        settings.TESTING = True

        resp = add_card(card_info)

        self.assertTrue(resp['status_code'] == 202)

    @patch('app.agents.visa.sentry')
    def test_visa_add_multi_cards(self, mock_sentry):
        card_info = [{
            'id': 1,
            'action_code': ActionCode.ADD,
            'date': 1475920002,
            'payment_token': 'ZWFirX98PzNjZFoJTuLZ9KK5qrt',
            'card_token': '1111111111111111111111112',
            'partner_slug': 'visa'
        },
            {
                'id': 2,
                'action_code': ActionCode.ADD,
                'date': 1475920002,
                'payment_token': 'I78VlnwUL0gBgp8aBNA9Q3gKpja',
                'card_token': '1111111111111111111111113',
                'partner_slug': 'visa'
            }
        ]

        settings.TESTING = True
        visa = Visa()
        resp = visa.create_cards(card_info)

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

    @patch('app.agents.visa.sentry')
    def _test_visa_add_real_cards(self, mock_sentry):
        settings.TESTING = True
        visa = Visa()
        # load list and chunk
        for card_info in chunks(real_list, 100):
            for card in card_info:
                card['action_code'] = ActionCode.ADD
            resp = visa.create_cards(card_info)

        self.assertTrue(resp['status_code'] == 202)


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]
