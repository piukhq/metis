import base64
import json
import time
from contextlib import suppress
from datetime import datetime
from enum import Enum
from uuid import uuid4

import requests
from loguru import logger
from requests.exceptions import ConnectionError, Timeout

from metis import settings
from metis.action import ActionCode
from metis.prometheus.metrics import (
    STATUS_FAILED,
    STATUS_OTHER_RETRY,
    STATUS_SUCCESS,
    STATUS_TIMEOUT_RETRY,
    push_metrics,
    unenrolment_counter,
    unenrolment_response_time_histogram,
    vop_activations_counter,
    vop_activations_processing_seconds_histogram,
    vop_deactivations_counter,
    vop_deactivations_processing_seconds_histogram,
)


class VOPResultStatus(str, Enum):
    FAILED = "Failed"
    SUCCESS = "Success"
    RETRY = "Retry"
    TIMEOUT = "Timeout"


class Visa:
    header = {"Content-Type": "application/json"}

    MAX_RETRIES = 3
    ERROR_MAPPING = {
        ActionCode.ACTIVATE_MERCHANT: {
            "SUCCESS": VOPResultStatus.SUCCESS,
            "1000": VOPResultStatus.FAILED,
            "1010": VOPResultStatus.FAILED,
            "2000": VOPResultStatus.FAILED,
            "3000": VOPResultStatus.RETRY,
            "4000": VOPResultStatus.RETRY,
            "5000": VOPResultStatus.RETRY,
            "6000": VOPResultStatus.RETRY,
            "7000": VOPResultStatus.FAILED,
            "RTMOACTVE01": VOPResultStatus.FAILED,
            "RTMOACTVE02": VOPResultStatus.FAILED,
            "RTMOACTVE03": VOPResultStatus.FAILED,
            "RTMOACTVE04": VOPResultStatus.FAILED,
            "RTMOACTVE05": VOPResultStatus.RETRY,
        },
        ActionCode.DELETE: {
            "SUCCESS": VOPResultStatus.SUCCESS,
            "1000": VOPResultStatus.FAILED,
            "1010": VOPResultStatus.FAILED,
            "2000": VOPResultStatus.FAILED,
            "3000": VOPResultStatus.RETRY,
            "4000": VOPResultStatus.RETRY,
            "5000": VOPResultStatus.RETRY,
            "6000": VOPResultStatus.RETRY,
            "7000": VOPResultStatus.FAILED,
            "RTMENRE0026": VOPResultStatus.SUCCESS,
            "RTMENRE0049": VOPResultStatus.FAILED,
            "RTMENRE0050": VOPResultStatus.FAILED,
        },
        ActionCode.DEACTIVATE_MERCHANT: {
            "SUCCESS": VOPResultStatus.SUCCESS,
            "1000": VOPResultStatus.FAILED,
            "1010": VOPResultStatus.FAILED,
            "2000": VOPResultStatus.FAILED,
            "3000": VOPResultStatus.RETRY,
            "4000": VOPResultStatus.RETRY,
            "5000": VOPResultStatus.RETRY,
            "6000": VOPResultStatus.RETRY,
            "7000": VOPResultStatus.FAILED,
            "RTMOACTVE01": VOPResultStatus.FAILED,
            "RTMOACTVE02": VOPResultStatus.FAILED,
            "RTMOACTVE03": VOPResultStatus.FAILED,
            "RTMOACTVE04": VOPResultStatus.FAILED,
            "RTMOACTVE05": VOPResultStatus.RETRY,
        },
        ActionCode.ADD: {
            "SUCCESS": VOPResultStatus.SUCCESS,
            "1000": VOPResultStatus.FAILED,
            "1010": VOPResultStatus.FAILED,
            "2000": VOPResultStatus.FAILED,
            "3000": VOPResultStatus.RETRY,
            "4000": VOPResultStatus.RETRY,
            "5000": VOPResultStatus.RETRY,
            "6000": VOPResultStatus.RETRY,
            "7000": VOPResultStatus.FAILED,
            "RTMENRE0003": VOPResultStatus.FAILED,
            "RTMENRE0005": VOPResultStatus.FAILED,
            "RTMENRE0008": VOPResultStatus.FAILED,
            "RTMENRE0011": VOPResultStatus.FAILED,
            "RTMENRE0015": VOPResultStatus.FAILED,
            "RTMENRE0016": VOPResultStatus.FAILED,
            "RTMENRE0017": VOPResultStatus.FAILED,
            "RTMENRE0019": VOPResultStatus.FAILED,
            "RTMENRE0021": VOPResultStatus.FAILED,
            "RTMENRE0022": VOPResultStatus.FAILED,
            "RTMENRE0023": VOPResultStatus.FAILED,
            "RTMENRE0025": VOPResultStatus.FAILED,
            "RTMENRE0028": VOPResultStatus.FAILED,
            "RTMENRE0032": VOPResultStatus.FAILED,
            "RTMENRE0035": VOPResultStatus.FAILED,
            "RTMENRE0039": VOPResultStatus.FAILED,
            "RTMENRE0042": VOPResultStatus.FAILED,
            "RTMENRE0044": VOPResultStatus.FAILED,
            "RTMENRE0049": VOPResultStatus.FAILED,
            "RTMENRE0052": VOPResultStatus.FAILED,
            "RTMENRE0053": VOPResultStatus.FAILED,
            "RTMENRE0054": VOPResultStatus.FAILED,
            "RTMENRE0055": VOPResultStatus.FAILED,
            "RTMENRE0056": VOPResultStatus.FAILED,
            "RTMENRE0057": VOPResultStatus.FAILED,
            "RTMENRE0058": VOPResultStatus.FAILED,
            "RTMENRE0059": VOPResultStatus.FAILED,
            "RTMENRE0060": VOPResultStatus.FAILED,
            "RTMENRE0061": VOPResultStatus.FAILED,
            "RTMENRE0071": VOPResultStatus.FAILED,
            "RTMENRE0072": VOPResultStatus.FAILED,
            "RTMENRE0075": VOPResultStatus.FAILED,
            "RTMENRE0077": VOPResultStatus.FAILED,
            "RTMENRE0078": VOPResultStatus.FAILED,
            "RTMENRE0080": VOPResultStatus.FAILED,
            "RTMENRE0081": VOPResultStatus.FAILED,
            "RTMENRE0082": VOPResultStatus.FAILED,
            "RTMENRE0083": VOPResultStatus.FAILED,
            "RTMENRE0084": VOPResultStatus.FAILED,
            "RTMENRE0085": VOPResultStatus.FAILED,
            "RTMENRE0086": VOPResultStatus.FAILED,
            "RTMENRE0087": VOPResultStatus.FAILED,
            "RTMENRE0088": VOPResultStatus.FAILED,
            "RTMENRE0089": VOPResultStatus.FAILED,
        },
    }

    def __init__(self):
        self.vop_enrol = "/vop/v1/users/enroll"
        self.vop_activation = "/vop/v1/activations/merchant"
        self.vop_deactivation = "/vop/v1/deactivations/merchant"
        self.vop_unenroll = "/vop/v1/users/unenroll"
        self.auth_type = "Basic"
        self.spreedly_receive_token = settings.Secrets.spreedly_visa_receive_token
        self.vop_community_code = settings.Secrets.vop_community_code
        self.vop_spreedly_community_code = settings.Secrets.vop_spreedly_community_code
        self.offerid = settings.Secrets.vop_offerid
        self.vop_user_id = settings.Secrets.vop_user_id
        self.vop_password = settings.Secrets.vop_password
        spreedly_vop_user_id = settings.Secrets.spreedly_vop_user_id
        spreedly_vop_password = settings.Secrets.spreedly_vop_password
        self.merchant_group = settings.Secrets.vop_merchant_group

        if settings.TESTING:
            # Staging
            self.vop_url = "https://cert.api.visa.com"
            self.spreedly_receive_token = "visa"

        elif settings.PRE_PRODUCTION:
            # PRE-PRODUCTION
            self.vop_url = "https://api.visa.com"
        else:
            # Production
            self.vop_url = "https://api.visa.com"
        self.spreedly_vop_auth_value = base64.b64encode(
            f"{spreedly_vop_user_id}:{spreedly_vop_password}".encode()
        ).decode("ascii")

        # Override  settings if stubbed
        if settings.TESTING and settings.STUBBED_VOP_URL:
            self.vop_url = settings.STUBBED_VOP_URL

    def receiver_token(self):
        return f"{self.spreedly_receive_token}/deliver.json"

    @property
    def spreedly_vop_headers(self):
        """
        :return: headers for Spreedly to talk to VOP, as a new line separated string for use in deliver body
        """
        return f"Authorization: {self.auth_type} {self.spreedly_vop_auth_value}\nContent-Type: application/json"

    @staticmethod
    def _log_success_response(resp_content, action_name):
        resp_user_details = resp_content.get("userDetails", {})
        resp_token = resp_user_details.get("externalUserId", "")
        message = f"Visa VOP {action_name} successful, Visa successfully processed"
        if resp_token:
            message = f"{message}; token {resp_token}"
        logger.info(message)
        return message

    @staticmethod
    def _log_error_response(resp_visa_status_code, action_name, add_message):
        if not add_message:
            add_message = "Could not access the PSP receiver"

        psp_message_list = [f"VOP_status_code: {resp_visa_status_code}", add_message]
        message = f'Problem with PSP call: Action: Visa {action_name}. Error:{" ".join(psp_message_list)}'
        logger.error(message)
        return message

    def check_success(  # noqa: PLR0913
        self,
        action_code,
        action_name,
        resp_content,
        resp_state,
        resp_visa_status,
        resp_visa_status_code,
        response_message,
    ):
        other_data = {"activation_id": None}
        if resp_state == VOPResultStatus.SUCCESS:
            if action_code == ActionCode.ACTIVATE_MERCHANT:
                activation_id = resp_content.get("activationId", None)
                if not activation_id:
                    resp_state = VOPResultStatus.FAILED
                    resp_visa_status_code = 0
                    response_message = "VOP reported success but no activationId returned"
                    resp_visa_status["activation_error"] = response_message
                    self._log_error_response(resp_visa_status_code, action_name, response_message)
                else:
                    other_data["activation_id"] = activation_id
                    self._log_success_response(resp_content, action_name)
            elif action_code == ActionCode.ADD:
                resp_user_details = {}
                try:
                    resp_user_details = resp_content.get("userDetails", {})
                    other_data["agent_card_uid"] = resp_user_details["cards"][0]["cardId"]
                except KeyError:
                    logger.error(
                        f"Could not Extract VOP CardId from success response: UserDetails: {resp_user_details}"
                    )
        else:
            self._log_error_response(resp_visa_status_code, action_name, response_message)

        return resp_state, resp_visa_status_code, response_message, other_data

    def process_vop_response(self, resp_content, response_status_code, action_name, action_code):
        status_mapping = self.ERROR_MAPPING[action_code]
        if not resp_content:
            resp_content = {}

        detailed_visa_status_code = ""
        detailed_visa_status_message = ""
        resp_visa_status = resp_content.get("responseStatus", {})
        resp_visa_status_code = resp_visa_status.get("code", "")

        resp_visa_status_message = resp_visa_status.get("message", "")
        resp_detail_list = resp_visa_status.get("responseStatusDetails", [])
        if len(resp_detail_list) > 0:
            resp_detail = resp_detail_list[0]

            with suppress(AttributeError):
                detailed_visa_status_code = resp_detail.get("code", "")
                detailed_visa_status_message = resp_detail.get("message", "")

        response_message = f"{resp_visa_status_message};{detailed_visa_status_message}"

        if detailed_visa_status_code and detailed_visa_status_code in status_mapping:
            resp_state = status_mapping[detailed_visa_status_code]
            resp_visa_status_code = detailed_visa_status_code
        elif resp_visa_status_code:
            resp_state = status_mapping.get(resp_visa_status_code, VOPResultStatus.FAILED)
        elif response_status_code >= 300:
            resp_state = VOPResultStatus.FAILED
        else:
            resp_state = VOPResultStatus.FAILED
            if not resp_visa_status_message:
                resp_visa_status_message = "No Visa status message"
            if not detailed_visa_status_message:
                detailed_visa_status_message = "No details given - Invalid VOP reply"
                response_message = f"{resp_visa_status_message};{detailed_visa_status_message}"

        return self.check_success(
            action_code,
            action_name,
            resp_content,
            resp_state,
            resp_visa_status,
            resp_visa_status_code,
            response_message,
        )

    @staticmethod
    def get_bink_status(resp_mapping_status_code, status_mapping):
        if resp_mapping_status_code in status_mapping:
            bink_status = status_mapping[resp_mapping_status_code]
        else:
            bink_status = status_mapping.get("BINK_UNKNOWN", 0)
        return bink_status

    def response_handler(self, response, action_name: str, status_mapping: dict) -> dict:
        """
        Legacy Response handler must have parameters in this form to be compatible with common service code
        For VOP This code is not used for activate, deactivate and unenroll
        :param response: VOP call response object
        :param action_name: name as a string passed from service
        :param status_mapping: mapping dict from Hermes which must prepend "action_name:" eg Add: or Delete:
        :return: response dict in with keys: "message", "status_code" and if success "bink_status"
        """
        try:
            resp_content = response.json()
        except AttributeError:
            resp_content = {}
        other_data = {}
        if not resp_content:
            resp_content = {}
        resp_transaction = resp_content.get("transaction", {})
        resp_response = resp_transaction.get("response", {})
        vop_response_status_code = resp_response.get("status", 0)
        vop_response_body_str = resp_response.get("body", "{}")
        action_code = ActionCode.ADD
        try:
            vop_response_body = json.loads(vop_response_body_str)
            resp_state, resp_visa_status_code, response_message, other_data = self.process_vop_response(
                vop_response_body, vop_response_status_code, action_name, action_code
            )
        except json.decoder.JSONDecodeError as error:
            resp_state = VOPResultStatus.FAILED
            resp_visa_status_code = "0"
            response_message = (
                f"Illegal json returned from VOP via Spreedly {error} " f"- got message: {vop_response_body_str}"
            )

        resp_mapping_status_code = f"{action_name}:{resp_visa_status_code}"
        return {
            "message": response_message,
            "status_code": vop_response_status_code,
            "response_state": resp_state.value,
            "agent_status_code": resp_mapping_status_code,
            "bink_status": self.get_bink_status(resp_mapping_status_code, status_mapping),
            "other_data": other_data,
        }

    def add_card_request_body(self, card_info):
        data = {
            "correlationId": str(uuid4()),
            "userDetails": {
                "communityCode": self.vop_spreedly_community_code,
                "userKey": card_info["payment_token"],
                "externalUserId": card_info["payment_token"],
                "cards": [{"cardNumber": "{{credit_card_number}}"}],
            },
            "communityTermsVersion": "1",
        }
        return json.dumps(data)

    def add_card_body(self, card_info):
        data = {
            "delivery": {
                "payment_method_token": card_info["payment_token"],
                "url": f"{self.vop_url}{self.vop_enrol}",
                "headers": self.spreedly_vop_headers,
                "body": self.add_card_request_body(card_info),
            }
        }

        return json.dumps(data)

    @staticmethod
    def _visa_report_vop_status_count(action_name, resp_state):
        states = {
            VOPResultStatus.FAILED: STATUS_FAILED,
            VOPResultStatus.SUCCESS: STATUS_SUCCESS,
            VOPResultStatus.RETRY: STATUS_OTHER_RETRY,
            VOPResultStatus.TIMEOUT: STATUS_TIMEOUT_RETRY,
        }
        if action_name == "Activate":
            vop_activations_counter.labels(status=states[resp_state]).inc()
        elif action_name == "Deactivate":
            vop_deactivations_counter.labels(status=states[resp_state]).inc()

    @staticmethod
    def _visa_report_vop_status_histogram(action_name, resp_time, resp_status_code):
        if action_name == "Activate":
            vop_activations_processing_seconds_histogram.labels(response_status_code=resp_status_code).observe(
                resp_time.total_seconds()
            )
        elif action_name == "Deactivate":
            vop_deactivations_processing_seconds_histogram.labels(response_status_code=resp_status_code).observe(
                resp_time.total_seconds()
            )

    def _basic_vop_request(self, api_endpoint, data):
        url = f"{self.vop_url}{api_endpoint}"
        headers = {"Content-Type": "application/json"}
        if settings.TESTING and settings.STUBBED_VOP_URL:
            logger.info(f"VOP Mock request to Pelops being sent to: {url}")
            return requests.request("POST", url, headers=headers, data=data, timeout=(5, 10))
        else:
            logger.info(
                f"VOP request being sent to {url} cert paths"
                f" {settings.Secrets.vop_client_certificate_path} and "
                f" {settings.Secrets.vop_client_key_path}"
            )
            return requests.request(
                "POST",
                url,
                auth=(self.vop_user_id, self.vop_password),
                cert=(settings.Secrets.vop_client_certificate_path, settings.Secrets.vop_client_key_path),
                headers=headers,
                data=data,
                timeout=(5, 10),
            )

    def try_vop_and_get_status(self, data, action_name, action_code, api_endpoint, card_id_info):  # noqa: PLR0913
        resp_state = VOPResultStatus.RETRY
        agent_status_code = None
        agent_message = ""
        retry_count = self.MAX_RETRIES
        json_data = json.dumps(data)
        other_data = {}

        while retry_count:
            retry_count -= 1
            try:
                response_start_time = datetime.now()
                response = self._basic_vop_request(api_endpoint, json_data)
                response_time = datetime.now() - response_start_time
                self._visa_report_vop_status_histogram(action_name, response_time, response.status_code)
                logger.info(
                    f"VOP {action_name} response for {card_id_info}:" f" {response.status_code}, {response.text}"
                )
                resp_state, agent_status_code, agent_message, other_data = self.process_vop_response(
                    response.json(), response.status_code, action_name, action_code
                )
                if resp_state == VOPResultStatus.RETRY:
                    self._visa_report_vop_status_count(action_name, resp_state)

            except json.decoder.JSONDecodeError as error:
                agent_message = f"Agent response was not valid JSON Error: {error}"
                logger.error(f"VOP {action_name} request for {card_id_info} exception error {agent_message}")
                agent_status_code = 0
                resp_state = VOPResultStatus.FAILED
                self._visa_report_vop_status_count(action_name, resp_state)

            except (Timeout, ConnectionError) as error:
                agent_message = f"Agent connection error: {error}"
                if retry_count == 0:
                    logger.error(f"VOP {action_name} request for {card_id_info} - {agent_message}")
                else:
                    logger.debug(f"VOP {action_name} request for {card_id_info} - {agent_message}")
                agent_status_code = 0
                resp_state = VOPResultStatus.RETRY
                self._visa_report_vop_status_count(action_name, VOPResultStatus.TIMEOUT)
                time.sleep(10)

            except Exception as error:
                agent_message = f"Agent exception {error}"
                logger.error(f"VOP {action_name} request for {card_id_info} exception error {agent_message}")
                agent_status_code = 0
                resp_state = VOPResultStatus.FAILED
                self._visa_report_vop_status_count(action_name, resp_state)

            if resp_state != VOPResultStatus.RETRY:
                retry_count = 0

        if resp_state == VOPResultStatus.SUCCESS:
            self._visa_report_vop_status_count(action_name, resp_state)
            status_code = 201
        else:
            self._visa_report_vop_status_count(action_name, VOPResultStatus.FAILED)
            status_code = 200

        full_agent_status_code = f"{action_name}:{agent_status_code}"
        logger.info(
            f"VOP {action_name} returned processed response for {card_id_info} Result: {status_code},"
            f"{resp_state}, code: {full_agent_status_code}, message: {agent_message}"
        )
        return resp_state.value, status_code, full_agent_status_code, agent_message, other_data

    @staticmethod
    def get_card_id_info(card_info):
        cid = card_info.get("id", "not sent")
        token = card_info.get("payment_token", "unknown")
        activation = ""
        if card_info.get("activation_id"):
            activation = f" activation_id: '{card_info['activation_id']}'"
        return f"Card id: '{cid}' userKey/token: '{token}'{activation}"

    def activate_data(self, payment_token, merchant_slug):
        return {
            "communityCode": self.vop_community_code,
            "userKey": payment_token,
            "offerId": self.offerid,
            "recurrenceLimit": "-1",
            "activations": [
                {"name": "MerchantGroupName", "value": self.merchant_group},
                {"name": "ExternalId", "value": merchant_slug},
            ],
        }

    def deactivate_data(self, payment_token, activation_id):
        return {
            "communityCode": self.vop_spreedly_community_code,
            "userKey": payment_token,
            "offerId": self.offerid,
            "clientCommunityCode": self.vop_community_code,
            "activationId": activation_id,
        }

    def activate_card(self, card_info):
        card_id_info = self.get_card_id_info(card_info)
        try:
            payment_token = card_info["payment_token"]
            merchant_slug = card_info["merchant_slug"]
            logger.info(f"VOP Metis Processing Activate request for merchant {merchant_slug}, {card_id_info}")
        except KeyError:
            logger.error(
                f"VOP Metis Activate request failed for {card_id_info} "
                f"due to missing payment_token or merchant slug"
            )
            self._visa_report_vop_status_count("Activate", VOPResultStatus.FAILED)
            return VOPResultStatus.FAILED.value, 400, "", "", {"activation_id": None}
        return self.try_vop_and_get_status(
            self.activate_data(payment_token, merchant_slug),
            "Activate",
            ActionCode.ACTIVATE_MERCHANT,
            self.vop_activation,
            card_id_info,
        )

    def deactivate_card(self, card_info):
        card_id_info = card_info.get("id", "not sent")
        try:
            payment_token = card_info["payment_token"]
            activation_id = card_info["activation_id"]
            logger.info(f"VOP Metis Processing DeActivate request for {card_id_info}")
        except KeyError:
            logger.error(
                f"VOP Metis DeActivate request failed for {card_id_info} due to missing"
                f" payment_token or activation_id"
            )
            self._visa_report_vop_status_count("Deactivate", VOPResultStatus.FAILED)
            return VOPResultStatus.FAILED.value, 400, "", "", {}

        return self.try_vop_and_get_status(
            self.deactivate_data(payment_token, activation_id),
            "Deactivate",
            ActionCode.DEACTIVATE_MERCHANT,
            self.vop_deactivation,
            card_id_info,
        )

    def un_enroll(self, card_info, action_name, pid):
        card_id_info = self.get_card_id_info(card_info)
        logger.info(f"VOP Metis processing unenrol request for {card_id_info}")
        try:
            data = {
                "correlationId": str(uuid4()),
                "communityCode": self.vop_spreedly_community_code,
                "userKey": card_info["payment_token"],
            }
        except KeyError:
            error_msg = f"VOP Metis Unenroll request failed for {card_id_info} due to missing payment_token"
            logger.error(error_msg)
            unenrolment_counter.labels(provider=card_info["partner_slug"], status=VOPResultStatus.FAILED.value).inc()
            push_metrics(pid)
            return VOPResultStatus.FAILED.value, 400, "", error_msg, {}

        vop_start_time = datetime.now()
        vop_unenroll = self.try_vop_and_get_status(
            data, action_name, card_info["action_code"], self.vop_unenroll, card_id_info
        )
        vop_finished_total_time = datetime.now() - vop_start_time

        unenrolment_counter.labels(provider=card_info["partner_slug"], status=vop_unenroll[0]).inc()
        unenrolment_response_time_histogram.labels(provider=card_info["partner_slug"], status=vop_unenroll[1]).observe(
            vop_finished_total_time.total_seconds()
        )

        push_metrics(pid)

        return vop_unenroll
