import unittest
import settings
from app.services import send_request, add_card, remove_card, get_agent


class TestServices(unittest.TestCase):

    def test_mastercard_enroll(self):
        card_info = {
            'payment_token': 'RjG4WgzYoBZWgJ1ZK3KsHd2nYRv',
            'card_token': ' ',
            'partner_slug': 'mastercard'
        }
        settings.TESTING = False

        resp = add_card(card_info)
        self.assertTrue(resp.status_code == 200)

    def test_mastercard_unenroll(self):
        card_info = {
            'payment_token': 'RjG4WgzYoBZWgJ1ZK3KsHd2nYRv',
            'card_token': ' ',
            'partner_slug': 'mastercard'
        }
        settings.TESTING = False

        resp = remove_card(card_info)
        self.assertTrue(resp.status_code == 200)

    def test_mastercard_do_echo(self):
        # Prod payment_token: RjG4WgzYoBZWgJ1ZK3KsHd2nYRv
        # MTF Payment token: WhtIyJrcpcLupNpBD4bSVx3qyY5
        card_info = {
            'payment_token': '4Bz7xSbcxCI0sHU9XN9lXvnvoMi',
            'card_token': ' ',
            'partner_slug': 'mastercard'
        }
        settings.TESTING = False

        resp = self.call_do_echo(card_info)
        self.assertTrue(resp.status_code == 200)

    def call_do_echo(self, card_info):
        """Once the receiver has been created and token sent back, we can pass in card details, without PAN.
        Receiver_tokens kept in settings.py."""
        # username = 'Yc7xn3gDP73PPOQLEB2BYpv31EV'
        # MTF receiver_token = 'XsXRs91pxREDW7TAFbUc1TgosxU' + '/deliver.xml'
        # Prod receiver_token = 'SiXfsuR5TQJ87wjH2O5Mo1I5WR' + '/deliver.xml'
        receiver_token = 'SiXfsuR5TQJ87wjH2O5Mo1I5WR' + '/deliver.xml'
        agent_instance = get_agent(card_info['partner_slug'])
        header = agent_instance.header
        url = 'https://core.spreedly.com/v1/receivers/' + receiver_token

        request_data = agent_instance.do_echo_body(card_info)

        resp = send_request('POST', url, header, request_data)
        return resp
