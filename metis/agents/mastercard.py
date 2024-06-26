import os
from typing import TYPE_CHECKING, ClassVar

import jinja2
from loguru import logger
from lxml import etree
from requests import Response

from metis.agents import AbstractAgentBase
from metis.settings import settings
from metis.vault import Secrets

if TYPE_CHECKING:
    from httpx import Response as HttpxResponse

MASTERCARD_DO_ECHO_URL = "https://services.mastercard.com/MRS/DiagnosticService"

# remove/reactivate constants used in mastercard requests
REACTIVATE = "1"
REMOVE = "3"


class MasterCard(AbstractAgentBase):
    header: ClassVar[dict] = {"Content-Type": "application/xml"}
    xml_header = "<![CDATA[Content-Type: text/xml;charset=utf-8]]>"

    def add_url(self) -> str:
        if settings.METIS_TESTING:
            return "http://latestserver.com/post.php"

        return "https://services.mastercard.com/MRS/CustomerService"

    def update_url(self) -> str:
        if settings.METIS_TESTING:
            return "http://latestserver.com/post.php"

        return "https://services.mastercard.com/MRS/CustomerService"

    def receiver_token(self) -> str:
        if settings.METIS_TESTING:
            return "mastercard" + "/deliver.xml"

        return f"{Secrets.spreedly_mastercard_receive_token}/deliver.xml"

    def response_handler(
        self,
        response: "HttpxResponse | Response",
        action_name: str,
        status_mapping: dict,
    ) -> dict:
        if response.status_code >= 300:
            logger.warning("Mastercard {} response: {}, body: {}", action_name, response, response.text)
            try:
                resp_content = response.json()
                psp_message = resp_content["errors"][0]["message"]
            except ValueError:
                psp_message = "Could not access the PSP receiver"

            message = f"Problem connecting to PSP. Action: MasterCard {action_name}. Error:{psp_message}"
            logger.error(message)
            return {
                "message": message,
                "status_code": response.status_code,
                "bink_status": status_mapping["BINK_UNKNOWN"],
            }

        fault = None
        try:
            xml_doc = etree.fromstring(response.text)
            string_elem = xml_doc.xpath("//body")[0].text
            xml_start_point = xml_doc.xpath("//body")[0].text.find("<?xml")
            soap_xml = string_elem[xml_start_point:]
            xml_soap_doc = etree.fromstring(soap_xml.encode("utf-8"))
            payment_method_token = xml_doc.xpath("//payment_method/token")
            fault = xml_soap_doc.xpath("//faultstring")
            fault_code_el = xml_soap_doc.xpath(
                "//ns2:code", namespaces={"ns2": "http://common.ws.mcrewards.mastercard.com/"}
            )

            fault_code = fault_code_el[0].text if fault_code_el else None
        except Exception:
            message = str(f"MasterCard {action_name} problem processing response.")
            logger.error(message, exc_info=1)

        if fault:
            # Not a good response, log the MasterCard error message and code, respond with 422 status
            message = "MasterCard {} unsuccessful - Token: {}, {}, {} {}".format(
                action_name, payment_method_token[0].text, fault[0].text, "Code:", fault_code
            )
            logger.info(message)
            resp = {
                "message": f"{action_name} MasterCard Fault recorded. Code: {fault_code}",
                "status_code": 422,
            }
        else:
            # could be a good response
            message = "MasterCard {} successful - Token: {}, {}".format(
                action_name, payment_method_token[0].text, "MasterCard successfully processed"
            )
            logger.info(message)
            resp = {"message": message, "status_code": response.status_code}

        if fault_code and fault_code in status_mapping:
            resp["bink_status"] = status_mapping[fault_code]
        else:
            resp["bink_status"] = status_mapping["BINK_UNKNOWN"]
        return resp

    def add_card_body(self, card_info: dict) -> str:
        xml_data = (
            "<delivery>"
            "  <payment_method_token>" + card_info["payment_token"] + "</payment_method_token>"
            "  <url>" + self.add_url() + "</url>"
            "  <headers>" + self.xml_header + "</headers>"
            "  <body>" + self.add_card_request_body(card_info) + "</body>"
            "</delivery>"
        )
        return xml_data

    def add_card_request_body(self, card_info: dict) -> str:
        # Add the card data method in once doEcho testing is complete.
        soap_xml = self.add_card_soap_template(card_info)
        body_data = "<![CDATA[" + soap_xml + "]]>"
        return body_data

    def add_card_soap_template(self, card_info: dict) -> str:
        template_env = self.jinja_environment()
        template_file = "mc_enroll_template.xml"
        template = template_env.get_template(template_file)

        template_vars = {
            "app_id": "",
            "institution_name": "loyaltyangels",
            "binary_security_token": "{{#binary_security_token}}{{/binary_security_token}}",
            "utc_timestamp1": "{{#utc_timestamp}}{{/utc_timestamp}}",
            "utc_timestamp2": "{{#utc_timestamp}}{{/utc_timestamp}}",
            "bank_customer_number": card_info["payment_token"],
            "member_ica": "17597",
            "bank_account_number": "{{credit_card_number}}",
            "account_status_code": "1",
            "bank_product_code": "MCCLA",
            "program_identifier": "LAVN",
        }
        output_text = template.render(template_vars)

        # Wrap the xml in {{#xmldsig}} tags for Spreedly to sign
        output_text = "{{#xml_dsig}}" + output_text + "{{/xml_dsig}}"
        return output_text

    def remove_card_body(self, card_info: dict) -> str:
        xml_data = (
            "<delivery>"
            "  <payment_method_token>" + card_info["payment_token"] + "</payment_method_token>"
            "  <url>" + self.update_url() + "</url>"
            "  <headers>" + self.xml_header + "</headers>"
            "  <body>" + self.remove_card_request_body() + "</body>"
            "</delivery>"
        )
        return xml_data

    def reactivate_card_body(self, card_info: dict) -> str:
        xml_data = (
            "<delivery>"
            "  <payment_method_token>" + card_info["payment_token"] + "</payment_method_token>"
            "  <url>" + self.update_url() + "</url>"
            "  <headers>" + self.xml_header + "</headers>"
            "  <body>" + self.reactivate_card_request_body() + "</body>"
            "</delivery>"
        )
        return xml_data

    def remove_card_request_body(self) -> str:
        soap_xml = self.soap_template(REMOVE)
        body_data = "<![CDATA[" + soap_xml + "]]>"
        return body_data

    def reactivate_card_request_body(self) -> str:
        soap_xml = self.soap_template(REACTIVATE)
        body_data = "<![CDATA[" + soap_xml + "]]>"
        return body_data

    def soap_template(self, action: str) -> str:
        template_env = self.jinja_environment()
        template_file = "mc_update_template.xml"
        template = template_env.get_template(template_file)

        template_vars = {
            "app_id": "{{credit_card_number}}",
            "institution_name": "loyaltyangels",
            "binary_security_token": "{{#binary_security_token}}{{/binary_security_token}}",
            "utc_timestamp1": "{{#utc_timestamp}}{{/utc_timestamp}}",
            "utc_timestamp2": "{{#utc_timestamp}}{{/utc_timestamp}}",
            "update_code": action,
        }
        output_text = template.render(template_vars)

        # Wrap the xml in {{#xmldsig}} tags for Spreedly to sign
        output_text = "{{#xml_dsig}}" + output_text + "{{/xml_dsig}}"
        return output_text

    def do_echo_body(self, card_info: dict) -> str:
        # DoEcho url MTF
        do_echo_url = MASTERCARD_DO_ECHO_URL
        xml_data = (
            "<delivery>"
            "  <payment_method_token>" + card_info["payment_token"] + "</payment_method_token>"
            "  <url>" + do_echo_url + "</url>"
            "  <headers>" + self.xml_header + "</headers>"
            "  <body>" + self.do_echo_request_body() + "</body>"
            "</delivery>"
        )
        return xml_data

    def do_echo_request_body(self) -> str:
        # MasterCards doEcho test request.
        soap_xml = self.do_echo_soap_template()
        body_data = "<![CDATA[" + soap_xml + "]]>"
        return body_data

    def do_echo_soap_template(self) -> str:
        template_env = self.jinja_environment()
        template_file = "mc_do_echo_template.xml"
        template = template_env.get_template(template_file)

        template_vars = {
            "app_id": 0,
            "institution_name": "loyaltyangels",
            "binary_security_token": "{{#binary_security_token}}{{/binary_security_token}}",
            "utc_timestamp1": "{{#utc_timestamp}}{{/utc_timestamp}}",
            "utc_timestamp2": "{{#utc_timestamp}}{{/utc_timestamp}}",
            "body": "Hello",
        }
        output_text = template.render(template_vars)

        # Wrap the xml in {{#xmldsig}} tags for Spreedly to sign
        output_text = "{{#xml_dsig}}" + output_text + "{{/xml_dsig}}"
        return output_text

    def jinja_environment(self) -> jinja2.Environment:
        template_path = os.path.join(os.path.dirname(__file__), "templates")
        template_loader = jinja2.FileSystemLoader(searchpath=template_path)
        template_env = jinja2.Environment(loader=template_loader)
        return template_env
