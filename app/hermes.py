import requests

from settings import HERMES_URL, SERVICE_API_KEY


def get_provider_status_mapping(slug):
    status_mapping = requests.get('{}/payment_cards/provider_status_mapping/{}'.format(HERMES_URL, slug)).json()
    return {x['provider_status']: x['bink_status'] for x in status_mapping}


def put_account_status(status_code, card_id=None, token=None):
    if not (card_id or token):
        raise AttributeError('You must pass either a card_id or token to put_account_status.')

    request_data = {'status': status_code}
    if card_id:
        request_data['id'] = card_id
    else:
        request_data['token'] = token

    return requests.put("{}/payment_cards/accounts/status/{}".format(HERMES_URL, card_id),
                        headers={'content-type': 'application/json',
                                 'Authorization': 'Token {}'.format(SERVICE_API_KEY)},
                        json=request_data)
