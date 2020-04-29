import settings
import json
import requests
from app.agents.agent_base import AgentBase
from uuid import uuid4


class Visa(AgentBase):
    header = {'Content-Type': 'application/json'}

    def __init__(self):
        self.vop_enrol = "/vop/v1/users/enroll"
        self.vop_activation = "/vop/v1/activations/merchant"
        self.vop_unenroll = "/vop/v1/users/unenroll"

        if settings.TESTING:
            # Test
            self.vop_community_code = "BINKCTE01"
            self.vop_url = "https://cert.api.visa.com"
            self.spreedly_receive_token = "visa"
            self.offerid = "48016"
            self.auth_type = 'Basic'
            self.auth_value = 'QWxhZGRpbjpvcGVuIHNlc2FtZQ=='
            self.merchant_group = "BIN_CAID_MRCH_GRP"

        else:
            # Production
            self.vop_community_code = "BINKCTE01"
            self.vop_url = "https://api.visa.com"
            self.spreedly_receive_token = "HwA3Nr2SGNEwBWISKzmNZfkHl6D"
            self.offerid = "48016"
            self.auth_type = 'Basic'
            self.auth_value = 'QWxhZGRpbjpvcGVuIHNlc2FtZQ=='
            self.merchant_group = "BIN_CAID_MRCH_GRP"

        # Override  settings if stubbed
        if settings.STUBBED_VOP_URL:
            self.vop_url = settings.STUBBED_VOP_URL

    def receiver_token(self):
        return f"{self.spreedly_receive_token}/deliver.json"

    @staticmethod
    def process_vop_response(response, action):
        resp_content = response.json()
        if not resp_content:
            resp_content = {}
        resp_visa_status = resp_content.get('responseStatus', {})
        resp_visa_status_code = resp_visa_status.get('code', '')

        if response.status_code >= 300 or not resp_visa_status_code:
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
            success = False
        else:
            success = True
            resp_user_details = resp_content.get('userDetails', {})
            resp_token = resp_user_details.get("externalUserId", 'unknown')
            message = "Visa VOP {} successful - Token: {}, {}".format(action, resp_token, "Visa successfully processed")
            settings.logger.info(message)
        resp_message = {'message': message, 'status_code': response.status_code}
        return success, resp_message, resp_visa_status_code

    def response_handler(self, response, action, status_mapping):
        success, resp_message, resp_visa_status_code = self.process_vop_response(response, action)
        if success:
            if resp_visa_status_code and resp_visa_status_code in status_mapping:
                resp_message['bink_status'] = status_mapping[resp_visa_status_code]
            else:
                resp_message['bink_status'] = status_mapping.get('BINK_UNKNOWN', "")
        return resp_message

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
                "headers": "Content-Type: application/json",
                "body": self.add_card_request_body(card_info),
            }
        }

        return json.dumps(data)

    def _basic_vop_request(self, api_endpoint, data):
        url = f"{self.vop_url}{api_endpoint}"
        return requests.request('POST', url, auth=(self.auth_type, self.auth_value), headers=self.header, data=data)

    def is_success(self, response, action):
        success, _, _ = self.process_vop_response(response, action)
        return success

    def activate_card(self, request_data):
        data = {
            "communityCode": self.vop_community_code,
            "userKey": request_data['payment_token'],
            "offerId": self.offerid,
            "recurrenceLimit": "-1",
            "activations": [
                {
                    "name": "MerchantGroupName",
                    "value": self.merchant_group
                },
                {
                    "name": "ExternalId",
                    "value": request_data['merchant_slug']
                }
            ]
        }
        return self.is_success(self._basic_vop_request(self.vop_activation, data), 'activate')

    def un_enroll(self, card_info):
        data = {
            "correlationId": str(uuid4()),
            "communityCode": self.vop_community_code,
            "userKey": card_info['payment_token'],
        }
        return self._basic_vop_request(self.vop_unenroll, data)
