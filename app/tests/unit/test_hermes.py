from unittest import TestCase
import json
import re

import httpretty

from app.hermes import get_provider_status_mapping, put_account_status
import settings


class TestHermes(TestCase):
    auth_key = 'Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL' \
        'CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU'

    def hermes_account_status_route(self):
        httpretty.register_uri(httpretty.PUT,
                               '{}/payment_cards/accounts/status'.format(settings.HERMES_URL),
                               status=200,
                               headers={'Authorization': self.auth_key},
                               content_type='application/json')

    def hermes_provider_status_mappings_route(self):
        httpretty.register_uri(httpretty.GET,
                               re.compile('{}/payment_cards/provider_status_mapping/(.+)'.format(settings.HERMES_URL)),
                               status=200,
                               headers={'Authorization': self.auth_key},
                               body=json.dumps([{'provider_status': 'BINK_UNKNOWN',
                                                 'bink_status': 10}]),
                               content_type='application/json')

    @httpretty.activate
    def test_get_provider_status_mapping(self):
        self.hermes_provider_status_mappings_route()
        mapping = get_provider_status_mapping('visa')
        self.assertEqual(mapping, {'BINK_UNKNOWN': 10})

    @httpretty.activate
    def test_put_account_status_card_id(self):
        self.hermes_account_status_route()
        put_account_status(2, card_id=2)
        self.assertTrue(httpretty.has_request())

    @httpretty.activate
    def test_put_account_status_card_token(self):
        self.hermes_account_status_route()
        put_account_status(2, token='test')
        self.assertTrue(httpretty.has_request())
