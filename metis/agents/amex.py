import json
import random
import time
from typing import TYPE_CHECKING, ClassVar

from loguru import logger
from lxml import etree
from requests import Response

from metis.agents import AbstractAgentBase
from metis.settings import settings
from metis.vault import Secrets

if TYPE_CHECKING:
    from httpx import Response as HttpxResponse
"""E2: https://api.qa.americanexpress.com/v2/datapartnership/offers/sync
E3: https://apigateway.americanexpress.com/v2/datapartnership/offers/sync"""
"""Amex use sync to add cards and unsync to remove cards from transactions output"""


port = "443"
res_path_sync = "/marketing/v4/smartoffers/card_accounts/cards/sync_details"
res_path_unsync = "/marketing/v4/smartoffers/card_accounts/cards/unsync_details"


class Amex(AbstractAgentBase):
    header: ClassVar[dict] = {"Content-Type": "application/xml"}
    partner_id = "AADP0050"
    distr_chan = "9999"  # 'Amex to provide'
    receiver_function_open = "{{#base64}}{{#bytes_hex}}{{#hmac}}sha256,"
    receiver_function_close = "{{/hmac}}{{/bytes_hex}}{{/base64}}"

    def __init__(self) -> None:
        # Amex OAuth details
        self.client_id = Secrets.amex_client_id
        self.client_secret = Secrets.amex_client_secret
        self.rec_token = f"{Secrets.spreedly_amex_receive_token}/deliver.xml"
        if settings.METIS_TESTING:
            self.url = settings.STUBBED_AMEX_URL
        else:
            # Production
            self.url = "https://apigateway2s.americanexpress.com"

    def add_url(self) -> str:
        return f"{self.url}{res_path_sync}"

    def remove_url(self) -> str:
        return f"{self.url}{res_path_unsync}"

    def receiver_token(self) -> str:
        return self.rec_token

    def request_header(self, res_path: str, req_body: str) -> str:
        mac_header = self.mac_api_header(res_path, req_body)
        auth = f'Authorization: "{mac_header}"'
        content_type = "Content-Type: application/json"
        api_key = f"X-AMEX-API-KEY: {self.client_id}"

        header = f"<![CDATA[{content_type}\n{auth}\n{api_key}]]>"
        return header

    def response_handler(
        self,
        response: "HttpxResponse | Response",
        action_name: str,
        status_mapping: dict,
    ) -> dict:
        if response.status_code >= 300:
            try:
                resp_content = response.json()
                psp_message = resp_content["errors"][0]["message"]
            except (ValueError, json.JSONDecodeError):
                psp_message = "Could not access the PSP receiver."

            message = f"Problem connecting to PSP. Action: Amex {action_name}. Error:{psp_message}"
            logger.error(message)
            return {"message": message, "status_code": response.status_code}

        try:
            xml_doc = etree.fromstring(response.text)
            payment_method_token = xml_doc.xpath("//payment_method/token")
            string_elem = xml_doc.xpath("//body")[0].text
            amex_data = json.loads(string_elem)
        except Exception:
            message = str({f"Amex {action_name} problem processing response."})
            resp = {"message": message, "status_code": 422}
            logger.error(message, exc_info=1)
        else:
            if amex_data["status"] == "Failure":
                # Not a good news response.
                message = "Amex {} unsuccessful - Token: {}, {}, {} {}".format(
                    action_name, payment_method_token[0].text, amex_data["respDesc"], "Code:", amex_data["respCd"]
                )
                logger.info(message)
                resp = {
                    "message": action_name + " Amex fault recorded. Code: " + amex_data["respCd"],
                    "status_code": 422,
                }
            else:
                # could be a good response
                message = "Amex {} successful - Token: {}, {}".format(
                    action_name, payment_method_token[0].text, "Amex successfully processed"
                )
                logger.info(message)

                resp = {"message": message, "status_code": 200}

            if amex_data and amex_data["respCd"] in status_mapping:
                resp["bink_status"] = status_mapping[amex_data["respCd"]]
            else:
                resp["bink_status"] = status_mapping["BINK_UNKNOWN"]

        return resp

    def add_card_request_body(self, card_info: dict) -> str:
        msg_id = str(int(time.time()))  # 'Can this be a guid or similar?'
        data = {
            "msgId": msg_id,
            "partnerId": self.partner_id,
            "cardNbr": "{{credit_card_number}}",
            "cmAlias1": card_info["payment_token"],
            "distrChan": self.distr_chan,
        }
        body_data = f"<![CDATA[{json.dumps(data)}]]>"
        return body_data

    def remove_card_request_body(self, card_info: dict) -> str:
        msg_id = str(int(time.time()))  # 'Can this be a guid or similar?'
        data = {
            "msgId": msg_id,
            "partnerId": self.partner_id,
            "cmAlias1": card_info["payment_token"],
            "distrChan": self.distr_chan,
        }
        body_data = f"<![CDATA[{json.dumps(data)}]]>"
        return body_data

    def add_card_body(self, card_info: dict) -> str:
        body = self.add_card_request_body(card_info)
        xml_data = (
            "<delivery>"
            "  <payment_method_token>" + card_info["payment_token"] + "</payment_method_token>"
            "  <url>" + self.add_url() + "</url>"
            "  <headers>" + self.request_header(res_path_sync, body) + "</headers>"
            "  <body>" + body + "</body>"
            "</delivery>"
        )
        return xml_data

    def remove_card_body(self, card_info: dict) -> str:
        body = self.add_card_request_body(card_info)
        xml_data = (
            "<delivery>"
            "  <payment_method_token>" + card_info["payment_token"] + "</payment_method_token>"
            "  <url>" + self.remove_url() + "</url>"
            "  <headers>" + self.request_header(res_path_unsync, body) + "</headers>"
            "  <body>" + body + "</body>"
            "</delivery>"
        )
        return xml_data

    def remove_cdata(self, input_string: str) -> str:
        output_string1 = input_string.replace("<![CDATA[", "")
        output_string2 = output_string1.replace("]]>", "")
        output_string3 = output_string2.replace(",", ",")
        return output_string3

    def mac_api_header(self, res_path_in: str, req_body: str) -> str:
        body_hash = self.remove_cdata(
            self.receiver_function_open + self.client_secret + "," + req_body + self.receiver_function_close
        )
        millis = int(round(time.time() * 1000))
        ts = millis
        random.seed(millis)
        post_fix = 10000000 + random.randint(0, 90000000)
        nonce = str(ts + post_fix) + ":AMEX"  # ":BINK"
        host = self.url.replace("https://", "")
        base_string = f"{ts!s}\n{nonce}\nPOST\n{res_path_in}\n{host}\n{port}\n{body_hash}\n"
        mac = self.receiver_function_open + self.client_secret + "," + base_string + self.receiver_function_close
        auth_header = f'MAC id="{self.client_id}",ts="{ts!s}",nonce="{nonce}",bodyhash="{body_hash}",mac="{mac}"'
        return auth_header
