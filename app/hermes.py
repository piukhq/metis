import requests

from settings import HERMES_URL


def provider_status_mapping(slug):
    status_mapping = requests.get('{}/payment_cards/provider_status_mapping/{}'.format(HERMES_URL, slug)).json()
    return {x['provider_status']: x['bink_status'] for x in status_mapping}
