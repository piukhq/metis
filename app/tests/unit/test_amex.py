from unittest import TestCase, mock
import httpretty
import json

import app.agents.amex as amex


class TestAmex(TestCase):
    def setUp(self):
        self.amex = amex.Amex()

        self.card_info = {'partner_slug': 'amex',
                          'payment_token': '3ERtq3pUV5OiNpdTCuhhXLBmnv8',
                          'card_token': ''}

    def test_url_testing(self):
        result = self.amex.add_url()
        self.assertEqual('https://api.qa.americanexpress.com/v3/smartoffers/sync', result)

        result = self.amex.remove_url()
        self.assertEqual('https://api.qa.americanexpress.com/v3/smartoffers/unsync', result)

    def test_receiver_token_testing(self):
        result = self.amex.receiver_token()
        self.assertIn('BqfFb1WnOwpbzH7WVTqmvYtffPV', result)

    def amex_route(self):
        auth_url = '{}{}'.format(amex.AMEX_URL, "/apiplatform/v2/oauth/token/mac")
        payload = "grant_type=client_credentials&scope="

        header = {"Content-Type": "application/x-www-form-urlencoded",
                  "Authentication": amex.mac_auth_header(),
                  "X-AMEX-API-KEY": amex.client_id}

        httpretty.register_uri(httpretty.POST,
                               '{}'.format(auth_url),
                               status=200,
                               headers=header,
                               body=payload,
                               content_type="application/x-www-form-urlencoded")

    @mock.patch('json.loads')
    @httpretty.activate
    def test_request_header(self, mock_loads):
        mock_loads.return_value = {"access_token": "1234567890", "mac_key": "99", }
        self.amex_route()
        result = self.amex.request_header(amex.res_path_sync)
        self.assertIn(result[:6], '<![CDATA[')
        self.assertIn(result[9:39], 'Content-Type: application/json')
        self.assertIn(result[40:55], 'Authorization: ')
        self.assertIn(result[169:219], 'X-AMEX-API-KEY: 91d207ec-267f-469f-97b2-883d4cfce44d')

    def test_remove_card_request_body(self):
        result = self.amex.remove_card_request_body(self.card_info)
        j = json.loads(result[9:-3])
        self.assertIn('msgId', j.keys())
        self.assertIn('partnerId', j.keys())
        self.assertIn('cardNbr', j.keys())
        self.assertIn('cmAlias1', j.keys())
        self.assertIn('distrChan', j.keys())

    def test_request_body_correct_text(self):
        result = self.amex.add_card_request_body(self.card_info)
        self.assertIn('{{credit_card_number}}', result)
        self.assertIn('cmAlias1', result)

    def test_mac_auth_header(self):
        result = amex.mac_auth_header()
        self.assertIn('MAC id', result)

    @mock.patch('json.loads')
    @httpretty.activate
    def test_add_card_body(self, mock_loads):
        mock_loads.return_value = {"access_token": "1234567890", "mac_key": "99", }
        self.amex_route()
        result = self.amex.add_card_body(self.card_info)
        self.assertIn('<delivery>', result)
        self.assertIn('<payment_method_token>', result)
        self.assertIn('<url>', result)
        self.assertIn('<headers>', result)
        self.assertIn('<body>', result)

    @mock.patch('json.loads')
    @httpretty.activate
    def test_remove_card_body(self, mock_loads):
        mock_loads.return_value = {"access_token": "1234567890", "mac_key": "99", }
        self.amex_route()
        result = self.amex.remove_card_body(self.card_info)
        self.assertIn('<delivery>', result)
        self.assertIn('<payment_method_token>', result)
        self.assertIn('<url>', result)
        self.assertIn('<headers>', result)
        self.assertIn('<body>', result)
