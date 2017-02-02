import json
import unittest
import httpretty
import re

from app.services import create_receiver, add_card, remove_card, get_agent
import app.agents.mastercard
import settings

auth_key = 'Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL' \
           'CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU'


class TestServices(unittest.TestCase):

    create_url = 'https://core.spreedly.com/v1/receivers.xml'
    payment_method_token = '3rkN9aJFfNEjvr2LqYZE4606hgG'
    receiver_token = 'XsXRs91pxREDW7TAFbUc1TgosxU'
    payment_url = 'https://core.spreedly.com/v1/receivers/' + receiver_token + '/deliver.xml'

    def create_route(self):
        xml_response = '<receiver>' \
            '<receiver_type>test</receiver_type>' \
            '<token>aDwu4ykovZVe7Gpto3rHkYWI5wI</token>' \
            '<hostnames>http://testing_latestserver.com</hostnames>' \
            '<state>retained</state>' \
            '<created_at type="dateTime">2016-04-06T07:54:13Z</created_at>' \
            '<updated_at type="dateTime">2016-04-06T07:54:13Z</updated_at>' \
            '<credentials nil="true"/>' \
            '</receiver>'

        httpretty.register_uri(httpretty.POST, self.create_url,
                               status=201,
                               body=xml_response,
                               content_type='application/xml')

    @staticmethod
    def hermes_status_route():
        httpretty.register_uri(httpretty.PUT, '{}/payment_cards/accounts/status'.format(settings.HERMES_URL),
                               status=200,
                               headers={'Authorization': auth_key},
                               body=json.dumps({"status_code": 200, "message": "success"}),
                               content_type='application/json')

    @staticmethod
    def hermes_provider_status_mappings_route():
        httpretty.register_uri(httpretty.GET,
                               re.compile('{}/payment_cards/provider_status_mapping/(.+)'.format(settings.HERMES_URL)),
                               status=200,
                               headers={'Authorization': auth_key},
                               body=json.dumps([{'provider_status': 'BINK_UNKNOWN',
                                                 'bink_status': 10}]),
                               content_type='application/json')

    def test_route(self):
        xml_data = """<transaction>
  <token>Rzvk2eGHx3jN8HlhzhWrHqzd3MS</token>
  <transaction_type>DeliverPaymentMethod</transaction_type>
  <state>succeeded</state>
  <created_at type="dateTime">2016-09-15T14:59:18Z</created_at>
  <updated_at type="dateTime">2016-09-15T14:59:20Z</updated_at>
  <succeeded type="boolean">true</succeeded>
  <message>Succeeded!</message>
  <url>https://ws.mastercard.com/mtf/MRS/CustomerService</url>
  <response>
    <status type="integer">200</status>
    <headers>
      <![CDATA[Content-Type: text/xml
Content-Length: 987
Date: Thu, 15 Sep 2016 14:59:19 GMT
Server: Information Not Disclosed]]>
    </headers>
    <body>
      <![CDATA[<?xml version="1.0" encoding="UTF-8"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/"><soapenv:Header xmlns:kd4="http://www.ibm.com/KD4Soap" xmlns:dat="http://mastercard.com/eis/bnb/servicev1_1/datatypes" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"></soapenv:Header><env:Body>Something here</env:Body></env:Envelope>]]>
    </body>
  </response>
  <receiver>
    <receiver_type>mastercard_mtf</receiver_type>
  </receiver>
  <payment_method>
    <token>RjG4WgzYoBZWgJ1ZK3KsHd2nYRv</token>
  </payment_method>
</transaction>"""  # noqa

        httpretty.register_uri(httpretty.POST, self.payment_url,
                               status=200,
                               body=xml_data,
                               content_type='application/xml')

    @httpretty.activate
    def test_create_receiver(self):
        self.create_route()
        resp = create_receiver('http://testing_latestserver.com', 'test')
        self.assertEqual(resp.status_code, 201)
        self.assertIn('token', resp.text)

    @httpretty.activate
    def test_add_card(self):
        card_info = {
            'id': 1,
            'payment_token': '1111111111111111111111',
            'card_token': '111111111111112',
            'partner_slug': 'mastercard'
        }

        self.test_route()
        app.agents.mastercard.testing_receiver_token = self.receiver_token
        self.hermes_status_route()
        self.hermes_provider_status_mappings_route()
        resp = add_card(card_info)
        self.assertEqual(200, resp['status_code'])

    @httpretty.activate
    def test_remove_card(self):
        card_info = {
            'id': 1,
            'payment_token': '1111111111111111111111',
            'card_token': '111111111111112',
            'partner_slug': 'mastercard'
        }

        self.test_route()
        app.agents.mastercard.testing_receiver_token = self.receiver_token
        resp = remove_card(card_info)
        self.assertEqual(200, resp['status_code'])

    def test_get_agent(self):
        agent_type = 'MasterCard'
        result = get_agent("mastercard")
        self.assertEqual(type(result).__name__, agent_type)
