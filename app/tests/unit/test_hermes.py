from unittest import TestCase
import json
import re

import httpretty

from app.hermes import provider_status_mapping
import settings


class TestHermes(TestCase):
    auth_key = 'Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL' \
        'CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU'

    def hermes_provider_status_mappings_route(self):
        httpretty.register_uri(httpretty.GET,
                               re.compile('{}/payment_cards/provider_status_mapping/(.+)'.format(settings.HERMES_URL)),
                               status=200,
                               headers={'Authorization': self.auth_key},
                               body=json.dumps([{'provider_status': 'BINK_UNKNOWN',
                                                 'bink_status': 10}]),
                               content_type='application/json')

    @httpretty.activate
    def test_provider_status_mapping(self):
        self.hermes_provider_status_mappings_route()
        mapping = provider_status_mapping('visa')
        self.assertEqual(mapping, {'BINK_UNKNOWN': 10})
