import unittest
import settings
from app.action import ActionCode
from app.agents.visa import Visa
from app.tests.unit.fixture import real_list


class TestServices(unittest.TestCase):

    """
    Visa agent is different from the other agents in that we call the agent directly to
    add or delete a card. Amex and MasterCard agents are called through the services module.
    So, to test Visa here we pass all the parameters, including action_code, in the card_info.
    """
    def test_visa_add_card(self):
        card_info = [{
            'id': 1,
            'payment_token': 'LyWyubSnJzQZtAxLvN8RYOYnSKv',
            'card_token': '1111111111111111111111112',
            'partner_slug': 'visa',
            'date': 1475920002,
            'action_code': ActionCode.ADD
        }]

        visa = Visa()
        settings.TESTING = True

        resp = visa.create_cards(card_info)

        self.assertTrue(resp['status_code'] == 202)

    def test_visa_add_multi_cards(self):
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

    def test_visa_add_card_wrong_token(self):
        card_info = [{
            'id': 1,
            'payment_token': 'teWyubSnJzQZtAxLvN8RYOYnS11',
            'card_token': '1111111111111111111111112',
            'partner_slug': 'visa',
            'date': 1475920002,
            'action_code': ActionCode.ADD
        }]

        visa = Visa()
        settings.TESTING = True

        resp = visa.create_cards(card_info)

        self.assertTrue(resp['status_code'] == 404)

    def test_visa_remove_card(self):
        card_info = [{
            'id': 1,
            'payment_token': 'LyWyubSnJzQZtAxLvN8RYOYnSKv',
            'card_token': '1111111111111111111111112',
            'partner_slug': 'visa',
            'date': 1475920002,
            'action_code': ActionCode.DELETE
        }]
        visa = Visa()
        settings.TESTING = True

        resp = visa.create_cards(card_info)
        self.assertTrue(resp.status_code == 200)

    def _test_visa_add_real_cards(self):
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
