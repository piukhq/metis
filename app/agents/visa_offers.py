import settings
import json
import requests
from app.agents.agent_base import AgentBase
from uuid import uuid4


class Visa(AgentBase):
    header = {'Content-Type': 'application/json'}

    def __init__(self):
        self.vop_enrol = "/v1/users/enroll"
        self.vop_activation = "/vop/v1/activations/merchant"

        if settings.TESTING:
            # Test
            self.vop_community_code = "BINKCTE01"
            self.vop_url = "https://cert.api.visa.com"
            self.spreedly_receive_token = "Visa"
            self.offerid = "48016"
            self.auth_type = 'Basic'
            self.auth_value = 'QWxhZGRpbjpvcGVuIHNlc2FtZQ=='
            self.merchant_group = "BIN_CAID_MRCH_GRP"

        else:
            # Production
            self.vop_community_code = "BINKCTE01"
            self.vop_url = "https://api.visa.com"
            self.spreedly_receive_token = "TBD"
            self.offerid = "48016"
            self.auth_type = 'Basic'
            self.auth_value = 'QWxhZGRpbjpvcGVuIHNlc2FtZQ=='
            self.merchant_group = "BIN_CAID_MRCH_GRP"

        # Override  settings if stubbed
        if settings.STUBBED_VOP_URL:
            self.vop_url = settings.STUBBED_VOP_URL

    def receiver_token(self):
        return f"{self.spreedly_receive_token}/deliver.json"

    def response_handler(self, response, action, status_mapping):
        # When the response is not clear the services code seems to set the error 'Could not access the PSP receiver'
        # However there is no failure exception around calling spreedly so this is not a true response. Kept here
        # for compatibility and will raise issue to investigate across all services in backlog.
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
            return {'message': message, 'status_code': response.status_code}

        resp_user_details = resp_content.get('userDetails', {})
        resp_token = resp_user_details.get("externalUserId", 'unknown')
        message = "Visa VOP {} successful - Token: {}, {}".format(action, resp_token, "Visa successfully processed")
        settings.logger.info(message)
        resp = {'message': message, 'status_code': response.status_code}

        if resp_visa_status_code and resp_visa_status_code in status_mapping:
            resp['bink_status'] = status_mapping[resp_visa_status_code]
        else:
            resp['bink_status'] = status_mapping.get('BINK_UNKNOWN', "")
        return resp

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
                "url": self.vop_url,
                "headers": "Content-Type: application/json",
                "body": self.add_card_request_body(card_info),
            }
        }

        return json.dumps(data)

    def activate_card(self, request_data):
        reply = {"status": "failed"}

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
        url = f"{self.vop_url}{self.vop_activation}"
        resp = requests.request('POST', url, auth=(self.auth_type, self.auth_value), headers=self.header, data=data)
        if resp.status_code < 300:
            success = None
            content = resp.json()
            state = content.get('responseStatus')
            if state:
                success = state.get('code')
            if success == "SUCCESS":
                reply['status'] = "activated"

        return reply

