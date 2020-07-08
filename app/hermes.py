import requests

from settings import HERMES_URL, SERVICE_API_KEY


def get_provider_status_mappings(slug):
    status_mapping = requests.get('{}/payment_cards/provider_status_mappings/{}'.format(HERMES_URL, slug),
                                  headers={'Content-Type': 'application/json',
                                           'Authorization': 'Token {}'.format(SERVICE_API_KEY)}).json()
    return {x['provider_status_code']: x['bink_status_code'] for x in status_mapping}


def put_account_status(status_code, card_id=None, token=None, **kwargs):
    if not (card_id or token):
        raise AttributeError('You must pass either a card_id or token to put_account_status.')

    if status_code:
        # Un-enrol sends retry status and success/error status update but not payment card status
        request_data = {'status': status_code}

    if id:
        request_data['id'] = card_id
    else:
        request_data['token'] = token

    for kwarg in kwargs:
        request_data[kwarg] = kwargs[kwarg]

    return requests.put("{}/payment_cards/accounts/status".format(HERMES_URL),
                        headers={'content-type': 'application/json',
                                 'Authorization': 'Token {}'.format(SERVICE_API_KEY)},
                        json=request_data)
