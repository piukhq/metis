import json
import unittest
from copy import copy

import arrow
import httpretty
from flask_testing import TestCase

import settings
from app import create_app
from app.action import ActionCode
from app.agents.visa_offers import Visa
from app.services import remove_card, add_card, get_spreedly_url

auth_key = 'Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL' \
           'CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU'


class Testing:
    TESTING = True


class VOPUnenroll(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        settings.TESTING = True
        cls.visa = Visa()
        cls.vop_un_enrol_url = f"{cls.visa.vop_url}{cls.visa.vop_unenroll}"
        cls.vop_deactivation_url = f"{cls.visa.vop_url}{cls.visa.vop_deactivation}"
        cls.hermes_payment_card_call_back = f"{settings.HERMES_URL}/payment_cards/accounts/status"

        cls.card_info = {
            "partner_slug": "visa",
            "payment_token": "psp_token",
            'card_token': "card_token",
            'id': 1234,
            'date': arrow.now().timestamp,
            "action_code": ActionCode.DELETE,
            "retry_id": -1
        }

    def register_success_requests(self):
        self.compile_requests(code="SUCCESS", message="Request proceed successfully without error.")

    def compile_requests(self, code, message):
        self.register_requests({
            "correlationId": "ce708e6a-fd5f-48cc-b9ff-ce518a6fda1a",
            "responseDateTime": "2020-01-29T15:02:50.8109336Z",
            "responseStatus": {
                    "code": code,
                    "message": message
            }
        })

    def register_requests(self, vop_response):
        httpretty.register_uri(
            httpretty.POST,
            self.vop_un_enrol_url,
            body=json.dumps(vop_response)
        )
        httpretty.register_uri(
            httpretty.PUT,
            self.hermes_payment_card_call_back,
            body=''
        )

    def register_deactivations(self, vop_response):
        httpretty.register_uri(
            httpretty.POST,
            self.vop_deactivation_url,
            body=json.dumps(vop_response)
        )

    def assert_success(self):
        request = httpretty.last_request()
        expected = {"id": 1234, "response_state": "Success", "response_status": "Delete:SUCCESS",
                    "response_message": "Request proceed successfully without error.;", "response_action": "Delete",
                    "retry_id": -1, "deactivated_list": [], "deactivate_errors": {}}
        actual = json.loads(request.body)
        self.assertDictEqual(expected, actual)

    def assert_failed(self, state, code, message):
        request = httpretty.last_request()
        expected = {"id": 1234, "response_state": state, "response_status": f"Delete:{code.upper()}",
                    "response_message": f"{message};", "response_action": "Delete",
                    "retry_id": -1, "deactivated_list": [], "deactivate_errors": {}}
        actual = json.loads(request.body)
        self.assertDictEqual(expected, actual)

    @httpretty.activate
    def test_remove_card_success(self):
        self.register_success_requests()
        remove_card(self.card_info)
        self.assert_success()

    @httpretty.activate
    def test_remove_card_fail(self):
        code = "1000"
        message = "Permanent VOP Error"
        self.compile_requests(code=code, message=message)
        remove_card(self.card_info)
        self.assert_failed("Failed", code, message)

    @httpretty.activate
    def test_remove_card_retry(self):
        code = "3000"
        message = "Temp VOP Error"
        self.compile_requests(code=code, message=message)
        remove_card(self.card_info)
        self.assert_failed("Retry", code, message)

    @httpretty.activate
    def test_remove_card_success_with_null_activations(self):
        self.register_success_requests()
        card_info = copy(self.card_info)
        card_info['activations'] = {}
        remove_card(card_info)
        self.assert_success()

    @httpretty.activate
    def test_remove_card_retry_with_null_activations(self):
        code = "3000"
        message = "Temp VOP Error"
        self.compile_requests(code=code, message=message)
        card_info = copy(self.card_info)
        card_info['activations'] = {}
        remove_card(self.card_info)
        self.assert_failed("Retry", code, message)

    @httpretty.activate
    def test_remove_card_success_with_activations(self):
        self.register_success_requests()
        self.register_deactivations({
            "correlationId": "96e38ed5-91d5-4567-82e9-6c441f4ca300",
            "responseDateTime": "2020-01-30T11:13:43.5765614Z",
            "responseStatus": {
                "code": "SUCCESS",
                "message": "Request proceed successfully without error."
            }
        })
        card_info = copy(self.card_info)
        card_info['activations'] = {
            345: {
                'scheme': "merchant1",
                'activation_id': "merchant1_activation_id"
            },
            6789: {
                'scheme': "merchant2",
                'activation_id': "merchant2_activation_id"
            }
        }
        remove_card(card_info)
        prev_req = httpretty.latest_requests()
        self.assertEqual(4, len(prev_req))
        req = json.loads(prev_req[0].body)
        self.assertEqual("merchant1_activation_id", req["activationId"])
        req = json.loads(prev_req[1].body)
        self.assertEqual("merchant2_activation_id", req["activationId"])
        req = json.loads(prev_req[3].body)
        self.assertEqual(1234, req["id"])
        self.assertEqual("Success", req["response_state"])
        self.assertEqual("Delete:SUCCESS", req["response_status"])
        self.assertEqual("Delete", req["response_action"])
        self.assertEqual([345, 6789], req["deactivated_list"])
        self.assertEqual(0, len(req["deactivate_errors"]))

    @httpretty.activate
    def test_remove_card_retry_with_activations(self):
        code = "3000"
        message = "Temp VOP Error"
        self.compile_requests(code=code, message=message)
        self.register_deactivations({
            "correlationId": "96e38ed5-91d5-4567-82e9-6c441f4ca300",
            "responseDateTime": "2020-01-30T11:13:43.5765614Z",
            "responseStatus": {
                "code": "SUCCESS",
                "message": "Request proceed successfully without error."
            }
        })
        card_info = copy(self.card_info)
        card_info['activations'] = {
            345: {
                'scheme': "merchant1",
                'activation_id': "merchant1_activation_id"
            },
            6789: {
                'scheme': "merchant2",
                'activation_id': "merchant2_activation_id"
            }
        }
        remove_card(self.card_info)
        self.assert_failed("Retry", code, message)
        prev_req = httpretty.latest_requests()
        self.assertEqual(4, len(prev_req))

    @httpretty.activate
    def test_remove_card_success_with_activation_retry(self):
        self.register_success_requests()
        self.register_deactivations({
            "activationId": "88395654-0b8a-4f2d-9046-2b8669f76bd2",
            "correlationId": "96e38ed5-91d5-4567-82e9-6c441f4ca300",
            "responseDateTime": "2020-01-30T11:13:43.5765614Z",
            "responseStatus": {
                "code": "3000",
                "message": "VOP DeActivate failure message.",
                "responseStatusDetails": []
            }
        })
        card_info = copy(self.card_info)
        card_info['activations'] = {
            345: {
                'scheme': "merchant1",
                'activation_id': "merchant1_activation_id"
            },
            6789: {
                'scheme': "merchant2",
                'activation_id': "merchant2_activation_id"
            }
        }
        remove_card(card_info)
        prev_req = httpretty.latest_requests()
        self.assertEqual(7, len(prev_req))
        req = json.loads(prev_req[0].body)
        self.assertEqual("merchant1_activation_id", req["activationId"])
        req = json.loads(prev_req[1].body)
        self.assertEqual("merchant1_activation_id", req["activationId"])
        req = json.loads(prev_req[2].body)
        self.assertEqual("merchant1_activation_id", req["activationId"])
        req = json.loads(prev_req[3].body)
        self.assertEqual("merchant2_activation_id", req["activationId"])
        req = json.loads(prev_req[4].body)
        self.assertEqual("merchant2_activation_id", req["activationId"])
        req = json.loads(prev_req[5].body)
        self.assertEqual("merchant2_activation_id", req["activationId"])
        req = json.loads(prev_req[6].body)
        self.assertEqual(1234, req["id"])
        self.assertEqual("Retry", req["response_state"])
        self.assertEqual("Delete", req["response_action"])
        self.assertEqual([], req["deactivated_list"])
        self.assertEqual(2, len(req["deactivate_errors"]))


class VOPEnroll(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        settings.TESTING = True
        settings.VOP_SPREEDLY_BASE_URL = "http://localhost:8006"
        cls.visa = Visa()
        cls.vop_enrol_url = f"{cls.visa.vop_url}{cls.visa.vop_enrol}"
        cls.hermes_payment_card_call_back = f"{settings.HERMES_URL}/payment_cards/accounts/status"
        cls.hermes_status_mapping = f"{settings.HERMES_URL}/payment_cards/provider_status_mappings/visa"

        cls.card_info = {
            "partner_slug": "visa",
            "payment_token": "psp_token",
            'card_token': "card_token",
            'id': 1234,
            'date': arrow.now().timestamp,
            "action_code": ActionCode.ADD,
            "retry_id": -1
        }

    def register_success_requests(self, card_info,
                                  resp_code="SUCCESS",
                                  message="Request proceed successfully without error.",
                                  vop_response_status_code=200):
        self.construct_request(card_info, resp_code, message, vop_response_status_code)

    def construct_request(self, card_info, resp_code, message, vop_response_status_code):
        body_dict = {
            "userDetails": {
                "externalUserId": "a74hd93d9812wir0174mk093dkie1",
                "communityCode": "BINKCTE01",
                "userId": "809902ef-3c0b-40b8-93bf-63e2621df06f",
                "userKey": "a74hd93d9812wir0174mk093dkie1",
                "languageId": "en-US",
                "timeZoneId": "Pacific Standard Time",
                "timeZoneShortCode": "PST",
                "cards": [
                    {
                        "cardId": "bfc33c1d-d4ef-e111-8d48-001a4bcdeef4",
                        "cardLast4": "1111",
                        "productId": "A",
                        "productIdDescription": "Visa Traditional",
                        "productTypeCategory": "Credit",
                        "cardStatus": "New"
                    }
                ],
                "userStatus": 1,
                "enrollDateTime": "2020-01-29T15:02:55.067"
            },
            "correlationId": "ce708e6a-fd5f-48cc-b9ff-ce518a6fda1a",
            "responseDateTime": "2020-01-29T15:02:55.1860039Z",
            "responseStatus": {
                "code": resp_code,
                "message": message,
                "responseStatusDetails": []
            }
        }
        self.register_requests(
            {
                "transaction": {
                    "response": {
                        "status": vop_response_status_code,
                        "body": json.dumps(body_dict)
                    }
                }
            }, card_info)

    def register_requests(self, vop_response, card_info):
        spreedly_url = f"{get_spreedly_url(card_info['partner_slug'])}/receivers/{self.visa.receiver_token()}"
        print(f"Mocking out {spreedly_url}")
        httpretty.register_uri(
            httpretty.POST,
            spreedly_url,
            body=json.dumps(vop_response)
        )
        print(f"Mocking out call back {self.hermes_payment_card_call_back}")
        httpretty.register_uri(
            httpretty.PUT,
            self.hermes_payment_card_call_back,
            body=''
        )
        print(f"Mocking out error mapping call back {self.hermes_payment_card_call_back}")
        httpretty.register_uri(
            httpretty.GET,
            self.hermes_status_mapping,
            body=json.dumps(
                [
                    {"provider_status_code": "Add:1000", "bink_status_code": 10},
                    {"provider_status_code": "Add:4000", "bink_status_code": 20}
                ]
            )
        )

        print("End points mocked")

    def assert_success(self):
        request = httpretty.last_request()
        expected = {"status": 1, "id": 1234, "response_state": "Success", "response_status": "Add:SUCCESS",
                    "response_status_code": 200,
                    "response_message": "Request proceed successfully without error.;", "response_action": "Add",
                    "retry_id": -1
                    }
        actual = json.loads(request.body)
        self.assertDictEqual(expected, actual)

    def assert_unsuccessful(self, code, message, resp_state, vop_response_status_code, mapped_status):
        request = httpretty.last_request()
        expected = {"status": mapped_status, "id": 1234, "response_state": resp_state, "response_status": f"Add:{code}",
                    "response_status_code": vop_response_status_code,
                    "response_message": f"{message};", "response_action": "Add",
                    "retry_id": -1
                    }
        actual = json.loads(request.body)
        self.assertDictEqual(expected, actual)

    @httpretty.activate
    def test_add_card_success(self):
        self.register_success_requests(self.card_info)
        try:
            add_card(self.card_info)
        except Exception as e:
            self.assertFalse(True, msg=f"Exception: {e}")
        prev_req = httpretty.latest_requests()
        for req in prev_req:
            print(req.body)
        self.assert_success()

    @httpretty.activate
    def test_add_card_failed(self):
        error_code = "1000"
        error_message = "Vop Permanent Failure message"
        vop_response_status_code = 400
        self.construct_request(self.card_info, error_code, error_message, vop_response_status_code)
        try:
            add_card(self.card_info)
        except Exception as e:
            self.assertFalse(True, msg=f"Exception: {e}")
        prev_req = httpretty.latest_requests()
        for req in prev_req:
            print(req.body)
        self.assert_unsuccessful(error_code, error_message, "Failed", vop_response_status_code, 10)

    @httpretty.activate
    def test_add_card_failed_unmapped(self):
        error_code = "xxxx"
        error_message = "Vop Permanent Failure message"
        vop_response_status_code = 400
        self.construct_request(self.card_info, error_code, error_message, vop_response_status_code)
        try:
            add_card(self.card_info)
        except Exception as e:
            self.assertFalse(True, msg=f"Exception: {e}")
        prev_req = httpretty.latest_requests()
        for req in prev_req:
            print(req.body)
        self.assert_unsuccessful(error_code, error_message, "Failed", vop_response_status_code, 0)

    @httpretty.activate
    def test_add_card_retry(self):
        error_code = "4000"
        error_message = "Vop Retry 4000 Failure message"
        vop_response_status_code = 400
        self.construct_request(self.card_info, error_code, error_message, vop_response_status_code)
        try:
            add_card(self.card_info)
        except Exception as e:
            self.assertFalse(True, msg=f"Exception: {e}")
        prev_req = httpretty.latest_requests()
        for req in prev_req:
            print(req.body)
        self.assert_unsuccessful(error_code, error_message, "Retry", vop_response_status_code, 20)

    @httpretty.activate
    def test_add_card_retry_unmapped(self):
        error_code = "3000"
        error_message = "Vop Retry 3000 Failure message"
        vop_response_status_code = 400
        self.construct_request(self.card_info, error_code, error_message, vop_response_status_code)
        try:
            add_card(self.card_info)
        except Exception as e:
            self.assertFalse(True, msg=f"Exception: {e}")
        prev_req = httpretty.latest_requests()
        for req in prev_req:
            print(req.body)
        self.assert_unsuccessful(error_code, error_message, "Retry", vop_response_status_code, 0)


class VOPActivation(TestCase):
    @classmethod
    def setUpClass(cls):
        settings.TESTING = True
        cls.visa = Visa()
        cls.vop_activation_url = f"{cls.visa.vop_url}{cls.visa.vop_activation}"
        cls.metis_activate_endpoint = "/visa/activate/"

        cls.card_info = {
            'payment_token': 'psp_token',
            'partner_slug': 'visa',
            'merchant_slug': "Merchant1",
            'id': 1234
        }

    def create_app(self):
        return create_app(Testing)

    def activate_request(self, card_info, vop_response):
        httpretty.register_uri(
            httpretty.POST,
            self.vop_activation_url,
            body=json.dumps(vop_response)
        )
        resp = self.client.post(self.metis_activate_endpoint,
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps(card_info))
        return resp

    def activation_unsuccessful(self, vop_error_code, vop_message):
        vop_response = {
            "correlationId": "96e38ed5-91d5-4567-82e9-6c441f4ca300",
            "responseDateTime": "2020-01-30T11:13:43.5765614Z",
            "responseStatus": {
                "code": vop_error_code,
                "message": vop_message
            }
        }
        resp = self.activate_request(self.card_info, vop_response)
        self.assertEqual(resp.status_code, 200)
        return resp

    @httpretty.activate
    def test_activation_success(self):
        vop_message = "Request proceed successfully without error."
        activation_id = "88395654-0b8a-4f2d-9046-2b8669f76bd2"
        vop_response = {
            "activationId": activation_id,
            "correlationId": "96e38ed5-91d5-4567-82e9-6c441f4ca300",
            "responseDateTime": "2020-01-30T11:13:43.5765614Z",
            "responseStatus": {
                "code": "SUCCESS",
                "message": vop_message
            }
        }
        resp = self.activate_request(self.card_info, vop_response)
        self.assertEqual(resp.status_code, 201)
        self.assertDictEqual(resp.json, {'response_status': 'Success', 'agent_response_code': 'Activate:SUCCESS',
                                         'agent_response_message': f'{vop_message};',
                                         'activation_id': activation_id})

    @httpretty.activate
    def test_activation_failed(self):
        vop_error_code = "RTMOACTVE01"
        vop_message = "VOP Activate failure message."
        resp = self.activation_unsuccessful(vop_error_code, vop_message)
        self.assertDictEqual(resp.json, {'response_status': 'Failed',
                                         'activation_id': None,
                                         'agent_response_code': f'Activate:{vop_error_code}',
                                         'agent_response_message': f'{vop_message};'})

    @httpretty.activate
    def test_activation_retry(self):
        vop_error_code = "RTMOACTVE05"
        vop_message = "VOP Activate failure message."
        resp = self.activation_unsuccessful(vop_error_code, vop_message)
        self.assertDictEqual(resp.json, {'response_status': 'Retry',
                                         'activation_id': None,
                                         'agent_response_code': f'Activate:{vop_error_code}',
                                         'agent_response_message': f'{vop_message};'})


class VOPDeActivation(TestCase):
    @classmethod
    def setUpClass(cls):
        settings.TESTING = True
        cls.visa = Visa()
        cls.vop_deactivation_url = f"{cls.visa.vop_url}{cls.visa.vop_deactivation}"
        cls.metis_deactivate_endpoint = "/visa/deactivate/"

        cls.card_info = {
            'payment_token': 'psp_token',
            'partner_slug': 'visa',
            'activation_id': 'activation_id',
            'id': 1234
        }

    def create_app(self):
        return create_app(Testing)

    def deactivate_request(self, card_info, vop_response):
        httpretty.register_uri(
            httpretty.POST,
            self.vop_deactivation_url,
            body=json.dumps(vop_response)
        )
        resp = self.client.post(self.metis_deactivate_endpoint,
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps(card_info))
        return resp

    def deactivation_unsuccessful(self, vop_error_code, vop_message):
        vop_response = {
            "correlationId": "96e38ed5-91d5-4567-82e9-6c441f4ca300",
            "responseDateTime": "2020-01-30T11:13:43.5765614Z",
            "responseStatus": {
                "code": vop_error_code,
                "message": vop_message
            }
        }
        resp = self.deactivate_request(self.card_info, vop_response)
        self.assertEqual(resp.status_code, 200)
        return resp

    @httpretty.activate
    def test_deactivation_success(self):
        vop_message = "Request proceed successfully without error."
        vop_response = {
            "correlationId": "96e38ed5-91d5-4567-82e9-6c441f4ca300",
            "responseDateTime": "2020-01-30T11:13:43.5765614Z",
            "responseStatus": {
                "code": "SUCCESS",
                "message": vop_message
            }
        }
        resp = self.deactivate_request(self.card_info, vop_response)
        self.assertEqual(resp.status_code, 201)
        self.assertDictEqual(resp.json, {'response_status': 'Success', 'agent_response_code': 'Deactivate:SUCCESS',
                                         'agent_response_message': f'{vop_message};'})

    @httpretty.activate
    def test_deactivation_failed(self):
        vop_error_code = "RTMOACTVE01"
        vop_message = "VOP DeActivate failure message."
        resp = self.deactivation_unsuccessful(vop_error_code, vop_message)
        self.assertDictEqual(resp.json, {'response_status': 'Failed',
                                         'agent_response_code': f'Deactivate:{vop_error_code}',
                                         'agent_response_message': f'{vop_message};'})

    @httpretty.activate
    def test_deactivation_retry(self):
        vop_error_code = "RTMOACTVE05"
        vop_message = "VOP DeActivate failure message."
        resp = self.deactivation_unsuccessful(vop_error_code, vop_message)
        self.assertDictEqual(resp.json, {'response_status': 'Retry',
                                         'agent_response_code': f'Deactivate:{vop_error_code}',
                                         'agent_response_message': f'{vop_message};'})


if __name__ == '__main__':
    unittest.main()
