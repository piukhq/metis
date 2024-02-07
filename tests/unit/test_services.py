import json
import re
import unittest

import httpretty

import metis.agents.mastercard
from metis.services import add_card, create_receiver, get_agent, reactivate_card
from metis.settings import settings

auth_key = (
    "Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL"
    "CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU"
)
xml_data = """<transaction>
  <token>Rzvk2eGHx3jN8HlhzhWrHqzd3MS</token>
  <transaction_type>DeliverPaymentMethod</transaction_type>
  <state>succeeded</state>
  <created_at type="dateTime">2016-09-15T14:59:18Z</created_at>
  <updated_at type="dateTime">2016-09-15T14:59:20Z</updated_at>
  <succeeded type="boolean">true</succeeded>
  <message>Succeeded!</message>
  <url>https://services.mastercard.com/mtf/MRS/CustomerService</url>
  <response>
    <status type="integer">200</status>
    <headers>
      <![CDATA[Content-Type: text/xml Content-Length: 987 Date: Thu, 15 Sep 2016 14:59:19 GMT Server: Information Not Disclosed]]>
    </headers>
    <body>
      <![CDATA[<?xml version="1.0" encoding="UTF-8"?>
      <env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
      <soapenv:Header xmlns:kd4="http://www.ibm.com/KD4Soap" xmlns:dat="http://mastercard.com/eis/bnb/servicev1_1/datatypes" xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"></soapenv:Header><env:Body>Something here</env:Body></env:Envelope>]]>
    </body>
  </response>
  <receiver>
    <receiver_type>mastercard_mtf</receiver_type>
  </receiver>
  <payment_method>
    <token>RjG4WgzYoBZWgJ1ZK3KsHd2nYRv</token>
  </payment_method>
</transaction>
"""  # noqa


class TestServices(unittest.TestCase):
    create_url = "https://core.spreedly.com/v1/receivers.xml"
    payment_method_token = "3rkN9aJFfNEjvr2LqYZE4606hgG"
    receiver_token = "mastercard"
    payment_url = "https://core.spreedly.com/v1/receivers/" + receiver_token + "/deliver.xml"

    def setUp(self) -> None:
        settings.METIS_TESTING = True

    def tearDown(self) -> None:
        settings.METIS_TESTING = False

    def create_route(self) -> None:
        xml_response = (
            "<receiver>"
            "<receiver_type>test</receiver_type>"
            "<token>aDwu4ykovZVe7Gpto3rHkYWI5wI</token>"
            "<hostnames>http://testing_latestserver.com</hostnames>"
            "<state>retained</state>"
            '<created_at type="dateTime">2016-04-06T07:54:13Z</created_at>'
            '<updated_at type="dateTime">2016-04-06T07:54:13Z</updated_at>'
            '<credentials nil="true"/>'
            "</receiver>"
        )

        httpretty.register_uri(
            httpretty.POST, self.create_url, status=201, body=xml_response, content_type="application/xml"
        )

    @staticmethod
    def hermes_status_route() -> None:
        httpretty.register_uri(
            httpretty.PUT,
            f"{settings.HERMES_URL}/payment_cards/accounts/status",
            status=200,
            headers={"Authorization": auth_key},
            body=json.dumps({"status_code": 200, "message": "success"}),
            content_type="application/json",
        )

    @staticmethod
    def hermes_provider_status_mappings_route() -> None:
        httpretty.register_uri(
            httpretty.GET,
            re.compile(f"{settings.HERMES_URL}/payment_cards/provider_status_mappings/(.+)"),
            status=200,
            headers={"Authorization": auth_key},
            body=json.dumps([{"provider_status_code": "BINK_UNKNOWN", "bink_status_code": 10}]),
            content_type="application/json",
        )

    def test_route(self) -> None:
        httpretty.register_uri(
            httpretty.POST, self.payment_url, status=200, body=xml_data, content_type="application/xml"
        )

    @httpretty.activate
    def test_add_card(self) -> None:
        card_info = {
            "id": 1,
            "payment_token": "1111111111111111111111",
            "card_token": "111111111111112",
            "partner_slug": "mastercard",
        }

        self.test_route()
        self.hermes_status_route()
        self.hermes_provider_status_mappings_route()
        assert (resp := add_card(card_info))
        self.assertEqual(200, resp["status_code"])

    def test_get_agent(self) -> None:
        result = get_agent("mastercard")
        self.assertIsInstance(result, metis.agents.mastercard.MasterCard)

    def test_get_invalid_agent(self) -> None:
        with self.assertRaises(KeyError):
            get_agent("monkey")  # type: ignore [arg-type] # this is the point of this test

    @httpretty.activate
    def test_reactivate_card(self) -> None:
        card_info = {
            "id": 1,
            "payment_token": "1111111111111111111111",
            "card_token": "111111111111112",
            "partner_slug": "mastercard",
        }

        self.test_route()
        self.hermes_status_route()
        self.hermes_provider_status_mappings_route()
        resp = reactivate_card(card_info)
        self.assertEqual(200, resp["status_code"])


class TestAsyncServices(unittest.IsolatedAsyncioTestCase):
    create_url = "https://core.spreedly.com/v1/receivers.xml"

    def setUp(self) -> None:
        settings.METIS_TESTING = True

    def tearDown(self) -> None:
        settings.METIS_TESTING = False

    def create_route(self) -> None:
        xml_response = (
            "<receiver>"
            "<receiver_type>test</receiver_type>"
            "<token>aDwu4ykovZVe7Gpto3rHkYWI5wI</token>"
            "<hostnames>http://testing_latestserver.com</hostnames>"
            "<state>retained</state>"
            '<created_at type="dateTime">2016-04-06T07:54:13Z</created_at>'
            '<updated_at type="dateTime">2016-04-06T07:54:13Z</updated_at>'
            '<credentials nil="true"/>'
            "</receiver>"
        )

        httpretty.register_uri(
            httpretty.POST, self.create_url, status=201, body=xml_response, content_type="application/xml"
        )

    @httpretty.activate
    async def test_create_receiver(self) -> None:
        self.create_route()
        resp = await create_receiver("http://testing_latestserver.com", "test")
        self.assertEqual(resp.status_code, 201)
        self.assertIn("token", resp.json())
