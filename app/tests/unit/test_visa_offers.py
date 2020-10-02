import json
import unittest

import arrow
import httpretty

import settings
from app.agents.visa_offers import Visa
from app.action import ActionCode
from app.services import remove_card
from copy import copy


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
        self.register_requests({
            "correlationId": "ce708e6a-fd5f-48cc-b9ff-ce518a6fda1a",
            "responseDateTime": "2020-01-29T15:02:50.8109336Z",
            "responseStatus": {
                    "code": "SUCCESS",
                    "message": "Request proceed successfully without error."
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
                    "retry_id": -1}
        actual = json.loads(request.body)
        self.assertDictEqual(expected, actual)

    @httpretty.activate
    def test_remove_card_success(self):
        self.register_success_requests()
        remove_card(self.card_info)
        self.assert_success()

    @httpretty.activate
    def test_remove_card_success_with_null_activations(self):
        self.register_success_requests()
        card_info = copy(self.card_info)
        card_info['activations'] = {}
        remove_card(card_info)
        self.assert_success()

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
        self.assert_success()
        prev_req = httpretty.latest_requests()
        self.assertEqual(6, len(prev_req))
        req1 = json.loads(prev_req[0].body)
        self.assertEqual("merchant1_activation_id", req1["activationId"])
        req2 = json.loads(prev_req[1].body)
        self.assertEqual("Deactivate:SUCCESS", req2["response_status"])
        req3 = json.loads(prev_req[2].body)
        self.assertEqual("merchant2_activation_id", req3["activationId"])
        req4 = json.loads(prev_req[3].body)
        self.assertEqual("Deactivate:SUCCESS", req4["response_status"])
        self.assertEqual(6, len(prev_req))

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
        self.assertEqual(8, len(prev_req))
        req = json.loads(prev_req[0].body)
        self.assertEqual("merchant1_activation_id", req["activationId"])
        req = json.loads(prev_req[1].body)
        self.assertEqual("merchant1_activation_id", req["activationId"])
        req = json.loads(prev_req[2].body)
        self.assertEqual("merchant1_activation_id", req["activationId"])
        req = json.loads(prev_req[3].body)
        self.assertEqual("Deactivate:3000", req["response_status"])
        req = json.loads(prev_req[4].body)
        self.assertEqual("merchant2_activation_id", req["activationId"])
        req = json.loads(prev_req[5].body)
        self.assertEqual("merchant2_activation_id", req["activationId"])
        req = json.loads(prev_req[6].body)
        self.assertEqual("merchant2_activation_id", req["activationId"])
        req = json.loads(prev_req[7].body)
        self.assertEqual("Deactivate:3000", req["response_status"])


if __name__ == '__main__':
    unittest.main()
