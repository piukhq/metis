import unittest
from app.services import remove_card
from unittest import mock
from app.card_router import ActionCode
import settings
import arrow
import httpretty
import json
from app.agents.visa_offers import Visa


class VOPUnenroll(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        settings.TESTING = True
        cls.visa = Visa()
        cls.vop_un_enrol_url = f"{cls.visa.vop_url}{cls.visa.vop_unenroll}"
        cls.hermes_payment_card_call_back = f"{settings.HERMES_URL}/payment_cards/accounts/status"


    @httpretty.activate
    def test_remove_card_success(self):
        card_info = {
            "partner_slug": "visa",
            "payment_token": "psp_token",
            'card_token': "card_token",
            'id': 1234,
            'date': arrow.now().timestamp,
 z            "action_code": ActionCode.DELETE
        }
        httpretty.register_uri(
            httpretty.POST,
            self.vop_un_enrol_url,
            body=json.dumps(
            {
                "responseStatus": {
                    "code": "SUCCESS", "message": "un-enrol equivalent to success", "responseStatusDetails": []
                }
            })
        )
        print(self.hermes_payment_card_call_back)
        httpretty.register_uri(
            httpretty.PUT,
            self.hermes_payment_card_call_back,
            body=''
        )
        remove_card(card_info)
        request = httpretty.last_request()
        expected = {"id": 1234, "response_state": "Success", "response_status": "Delete:SUCCESS",
                    "response_message": "un-enrol equivalent to success;", "response_action": "Delete",
                    "retry_id": -1}
        actual = json.loads(request.body)
        self.assertDictEqual(expected, actual)
        prev_req = httpretty.latest_requests()
        print(prev_req[0].body)
        print(prev_req[1].body)



if __name__ == '__main__':
    unittest.main()
