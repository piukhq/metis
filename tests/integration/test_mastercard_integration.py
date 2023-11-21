import json
import unittest

import httpretty

from metis import settings
from metis.services import add_card, get_agent, remove_card, send_request


class TestServices(unittest.TestCase):
    def setUp(self):
        httpretty.enable()
        self.mock_response = """
                <transaction>
                    <token>bink_mastercard_token_1</token>
                    <state>succeeded</state>
                    <succeeded type="boolean">true</succeeded>
                    <message>Succeeded!</message>
                    <response>
                        <headers><![CDATA[Content-Type: text/xml]]></headers>
                        <body><![CDATA[<?xml version='1.0' encoding='UTF-8'?>
                            <env:Envelope xmlns:env='http://schemas.xmlsoap.org/soap/envelope/'>
                                <soapenv:Header xmlns:kd4='http://www.ibm.com/KD4Soap'
                                    xmlns:dat='http://mastercard.com/eis/bnb/servicev1_1/datatypes'
                                    xmlns:soap='http://www.w3.org/2003/05/soap-envelope'
                                    xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/'>
                                    <kd4:KD4SoapHeaderV2>PRODESB4_KSC|3891838701|160923075124679</kd4:KD4SoapHeaderV2>
                                    <dat:bridgeUniqId>PRODESB4_KSC|3891838701|160923075124679</dat:bridgeUniqId>
                                </soapenv:Header>
                                <env:Body>
                                    <ns1:doEchoResponse xmlns:ns1='http://diagnostic.ws.mcrewards.mastercard.com/'>
                                        Hello Hello
                                    </ns1:doEchoResponse>
                                </env:Body>
                            </env:Envelope>]]>
                        </body>
                    </response>
                    <payment_method>
                        <token>RjG4WgzYoBZWgJ1ZK3KsHd2nYRv</token>
                    </payment_method>
                </transaction>
            """
        httpretty.register_uri(
            httpretty.POST,
            "https://core.spreedly.com/v1/receivers/mastercard/deliver.xml",
            body=self.mock_response,
            content_type="application/xml",
        )
        self.expected_response = [
            {"provider": "mastercard", "provider_status_code": "BINK_UNKNOWN", "bink_status_code": 200},
        ]
        httpretty.register_uri(
            httpretty.GET,
            "http://127.0.0.1:5010/payment_cards/provider_status_mappings/mastercard",
            body=json.dumps(self.expected_response),
            content_type="application/json",
            status=200,
        )

    def tearDown(self):
        httpretty.disable()
        httpretty.reset()

    def test_mastercard_enroll(self):
        card_info = {
            "payment_token": "RjG4WgzYoBZWgJ1ZK3KsHd2nYRv",
            "card_token": " ",
            "partner_slug": "mastercard",
            "id": 100,
        }
        settings.TESTING = True
        httpretty.register_uri(
            httpretty.PUT,
            "http://127.0.0.1:5010/payment_cards/accounts/status",
            body=json.dumps(self.expected_response),
            content_type="application/json",
            status=200,
        )
        resp = add_card(card_info)
        self.assertTrue(resp["status_code"] == 200)

    def test_mastercard_unenroll(self):
        card_info = {"payment_token": "RjG4WgzYoBZWgJ1ZK3KsHd2nYRv", "card_token": " ", "partner_slug": "mastercard"}
        settings.TESTING = True
        resp = remove_card(card_info)
        self.assertTrue(resp["status_code"] == 200)

    def test_mastercard_do_echo(self):
        card_info = {"payment_token": "4Bz7xSbcxCI0sHU9XN9lXvnvoMi", "card_token": " ", "partner_slug": "mastercard"}
        settings.TESTING = True

        resp = self.call_do_echo(card_info)
        self.assertTrue(resp.status_code == 200)

    def call_do_echo(self, card_info):
        """Once the receiver has been created and token sent back, we can pass in card details, without PAN.
        Receiver_tokens kept in settings.py."""
        receiver_token = "SiXfsuR5TQJ87wjH2O5Mo1I5WR" + "/deliver.xml"
        agent_instance = get_agent(card_info["partner_slug"])
        header = agent_instance.header
        url = "https://core.spreedly.com/v1/receivers/" + receiver_token

        request_data = agent_instance.do_echo_body(card_info)
        httpretty.register_uri(
            httpretty.POST,
            "https://core.spreedly.com/v1/receivers/SiXfsuR5TQJ87wjH2O5Mo1I5WR/deliver.xml",
            body=self.mock_response,
            content_type="application/xml",
        )

        resp = send_request("POST", url, header, request_data)
        return resp
