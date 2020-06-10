import json
from enum import Enum
from uuid import uuid4
from time import sleep
import requests
import base64
import settings
from app.card_router import ActionCode


class VOPResultStatus(str, Enum):
    FAILED = 'Failed'
    SUCCESS = 'Success'
    RETRY = 'Retry'


def cache_vop_security_data():
    vop_bink_client_cer = ""
    vop_bink_client_key = ""
    # When reading the vault on start up we may need a retry loop with a sleep
    sleep(1)
    if vop_bink_client_key and vop_bink_client_cer:
        try:
            with open(settings.VOP_CLIENT_KEY_PATH, 'w') as file:
                file.write(vop_bink_client_key)
            with open(settings.VOP_CLIENT_CER_PATH, 'w') as file:
                file.write(vop_bink_client_cer)
        except Exception as err:
            message = f"FAILED VOP Client Certificates were not installed on /temp. Error: {err}"
            settings.logger.error(message)
        else:
            message = "Success VOP Client Certificates correctly installed on /temp"
            settings.logger.info(message)
    else:
        message = f"FAILED VOP Client Certificates could not be read from Vault."
        settings.logger.error(message)


# This runs when the module is first loaded
cache_vop_security_data()


class Visa:
    header = {'Content-Type': 'application/json'}

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
            "RTMOACTVE05": VOPResultStatus.RETRY
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

        if settings.TESTING:
            # Staging
            self.vop_community_code = "BINKCTE01"
            self.vop_url = "https://cert.api.visa.com"
            self.spreedly_receive_token = "LsMTji00tyfJuXRelZmgRMs3s29"
            self.offerid = "48016"
            self.auth_type = 'Basic'
            self.vop_user_id = 'O8LIJL087433HBEFINYP21XvJukeEFn-VPS2lb1xgJ_tfwmEY'
            self.vop_password = 'VcEOK6Crx37TZef10LN6sG7zMAwnC9t9p9Yuz'
            spreedly_vop_user_id = '2GB20ZMDO1T6C5UG5JBT21a8v98h-dDnWJ347eaRdVASvwoA8'
            spreedly_vop_password = 'dOffXkB9OG6A0ZOU7IBAYf7Y709qs7zEqrFORLD'
            self.merchant_group = "BIN_CAID_MRCH_GRP"

        elif settings.PRE_PRODUCTION:
            # PRE-PRODUCTION
            self.vop_community_code = "BINKCL"
            self.vop_url = "https://api.visa.com"
            self.spreedly_receive_token = "LsMTji00tyfJuXRelZmgRMs3s29"
            self.offerid = "102414"
            self.auth_type = 'Basic'
            self.vop_user_id = 'FOQJBR614G1XCY1K687H21xqVQjpmmYApS77BSHxJIwF7he4w'
            self.vop_password = '73RkA59eWWosyB133Tt3rh556gBvvelVF17f'
            spreedly_vop_user_id = '2GB20ZMDO1T6C5UG5JBT21a8v98h-dDnWJ347eaRdVASvwoA8'
            spreedly_vop_password = 'dOffXkB9OG6A0ZOU7IBAYf7Y709qs7zEqrFORLD'
            self.merchant_group = "BIN_CAID_MRCH_GRP"

        else:
            # Production
            self.vop_community_code = "BINKCL"
            self.vop_url = "https://api.visa.com"
            self.spreedly_receive_token = "LsMTji00tyfJuXRelZmgRMs3s29"
            self.offerid = "102414"
            self.auth_type = 'Basic'
            self.vop_user_id = 'FOQJBR614G1XCY1K687H21xqVQjpmmYApS77BSHxJIwF7he4w'
            self.vop_password = '73RkA59eWWosyB133Tt3rh556gBvvelVF17f'
            spreedly_vop_user_id = '2GB20ZMDO1T6C5UG5JBT21a8v98h-dDnWJ347eaRdVASvwoA8'
            spreedly_vop_password = 'dOffXkB9OG6A0ZOU7IBAYf7Y709qs7zEqrFORLD'
            self.merchant_group = "BIN_CAID_MRCH_GRP"

        self.spreedly_vop_auth_value = base64.b64encode(
            f'{spreedly_vop_user_id}:{spreedly_vop_password}'.encode('utf8')).decode('ascii')

        # Override  settings if stubbed
        if settings.STUBBED_VOP_URL:
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
        resp_user_details = resp_content.get('userDetails', {})
        resp_token = resp_user_details.get("externalUserId", 'unknown')
        message = f"Visa VOP {action_name} successful - Token: {resp_token}, Visa successfully processed"
        settings.logger.info(message)
        return message

    @staticmethod
    def _log_error_response(response, resp_visa_status, resp_visa_status_code, action):
        settings.logger.warning("Visa {} response: {}, body: {}".format(action, response, response.text))
        status_errors = "".join(resp_visa_status.get('responseStatusDetails', ['None']))
        psp_message_list = [
            resp_visa_status.get('message', 'Could not access the PSP receiver'),
            f"with code: {resp_visa_status_code} Details: ",
            status_errors
        ]
        psp_message = "".join(psp_message_list)
        message = 'Problem connecting to PSP. Action: Visa {}. Error:{}'.format(action, psp_message)
        settings.logger.error(message)
        return message

    def process_vop_response(self, response, action_name, action_code):
        status_mapping = self.ERROR_MAPPING[action_code]
        resp_content = response.json()
        if not resp_content:
            resp_content = {}
        resp_visa_status = resp_content.get('responseStatus', {})
        resp_visa_status_code = resp_visa_status.get('code', '')

        if response.status_code >= 300 or not resp_visa_status_code:
            resp_status = VOPResultStatus.RETRY
        else:
            resp_status = status_mapping.get(resp_visa_status_code, VOPResultStatus.FAILED)

        if resp_status == VOPResultStatus.SUCCESS:
            self._log_success_response(resp_content, action_name)
        else:
            self._log_error_response(response, resp_visa_status, resp_visa_status_code, action_name)

        return resp_status, resp_visa_status_code

    @staticmethod
    def get_bink_status(resp_mapping_status_code, status_mapping):
        if resp_mapping_status_code in status_mapping:
            bink_status = status_mapping[resp_mapping_status_code]
        else:
            bink_status = status_mapping.get('BINK_UNKNOWN', "")
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
        resp_content = response.json()
        if not resp_content:
            resp_content = {}
        resp_visa_status = resp_content.get('responseStatus', {})
        resp_visa_status_code = resp_visa_status.get('code', '')

        if response.status_code >= 300 or not resp_visa_status_code:
            message = self._log_error_response(response, resp_visa_status, resp_visa_status_code, action_name)
            return {'message': message, 'status_code': response.status_code}

        message = self._log_success_response(resp_content, action_name)
        resp_mapping_status_code = f"{action_name}:{resp_visa_status_code}"
        return {
            'message': message,
            'status_code': response.status_code,
            'bink_status': self.get_bink_status(resp_mapping_status_code, status_mapping)
        }

    def add_card_request_body(self, card_info):
        data = {
            "correlationId": str(uuid4()),
            "userDetails": {
                "communityCode": self.vop_community_code,
                "userKey": card_info['payment_token'],
                "externalUserId": card_info['payment_token'],
                "cards": [{
                    "cardNumber": "{{credit_card_number}}"
                }]
            },
            "communityTermsVersion": "1"
        }
        return json.dumps(data)

    def add_card_body(self, card_info):
        data = {
            "delivery": {
                "payment_method_token": card_info['payment_token'],
                "url": f"{self.vop_url}{self.vop_enrol}",
                "headers": self.spreedly_vop_headers,
                "body": self.add_card_request_body(card_info),
            }
        }

        return json.dumps(data)

    def _basic_vop_request(self, api_endpoint, data):
        url = f"{self.vop_url}{api_endpoint}"
        headers = {'Content-Type': 'application/json'}
        return requests.request(
            'POST', url, auth=(self.vop_user_id, self.vop_password),
            cert=(settings.VOP_CLIENT_CER_PATH, settings.VOP_CLIENT_KEY_PATH),
            headers=headers, data=data)

    def try_vop_and_get_status(self, data, action_name, action_code, api_endpoint):
        resp_status = VOPResultStatus.RETRY
        agent_status_code = None
        retry_count = self.MAX_RETRIES

        while retry_count:
            retry_count -= 1
            try:
                response = self._basic_vop_request(api_endpoint, data)
                resp_status, agent_status_code = self.process_vop_response(response, action_name, action_code)
            except json.decoder.JSONDecodeError as error:
                agent_status_code = f"Agent response was not valid JSON Error: {error}"
                resp_status = VOPResultStatus.RETRY
            except Exception as error:
                agent_status_code = error
                resp_status = VOPResultStatus.RETRY

            if resp_status != VOPResultStatus.RETRY:
                retry_count = 0

        status_code = 201 if resp_status == VOPResultStatus.SUCCESS else 200
        full_agent_status_code = f"{action_name}:{agent_status_code}"
        return resp_status.value, status_code, full_agent_status_code

    def is_success(self, response, action, action_code):
        resp_status, _ = self.process_vop_response(response, action, action_code)
        if resp_status == VOPResultStatus.SUCCESS:
            return True

        return False

    def activate_deactivate_data(self, card_info):
        return {
            "communityCode": self.vop_community_code,
            "userKey": card_info['payment_token'],
            "offerId": self.offerid,
            "recurrenceLimit": "-1",
            "activations": [
                {
                    "name": "MerchantGroupName",
                    "value": self.merchant_group
                },
                {
                    "name": "ExternalId",
                    "value": card_info['partner_slug']
                }
            ]
        }

    def activate_card(self, card_info):
        return self.try_vop_and_get_status(
            self.activate_deactivate_data(card_info),
            "Activate",
            ActionCode.ACTIVATE_MERCHANT,
            self.vop_activation
        )

    def deactivate_card(self, card_info):
        return self.try_vop_and_get_status(
            self.activate_deactivate_data(card_info),
            "Deactivate",
            ActionCode.DEACTIVATE_MERCHANT,
            self.vop_deactivation
        )

    def un_enroll(self, card_info, action_name):
        data = {
            "correlationId": str(uuid4()),
            "communityCode": self.vop_community_code,
            "userKey": card_info['payment_token'],
        }
        return self.try_vop_and_get_status(data, action_name, card_info['action_code'], self.vop_unenroll)
