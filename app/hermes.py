import requests

from settings import HERMES_URL, SERVICE_API_KEY


def get_provider_status_mapping(slug):
    status_mapping = requests.get('{}/payment_cards/provider_status_mapping/{}'.format(HERMES_URL, slug)).json()
    return {x['provider_status']: x['bink_status'] for x in status_mapping}


def put_account_status(card_id, status_code):
    return requests.put("{}/payment_cards/accounts/status/{}".format(HERMES_URL, card_id),
                        headers={'content-type': 'application/json',
                                 'Authorization': 'Token {}'.format(SERVICE_API_KEY)},
                        json={"status": status_code})
