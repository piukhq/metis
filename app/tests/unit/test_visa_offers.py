import json
import logging
from unittest import TestCase, mock
from uuid import uuid4

import httpretty
from settings import HERMES_URL
import settings
from app.agents.visa_offers import Visa
from app.card_router import ActionCode
from app.services import remove_card

auth_key = 'Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL' \
           'CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU'


class ResponseMock:

    def __init__(self, data, status_code=200):
        self.data = data
        self.status = status_code

    def json(self):
        return json.loads(self.data)

    @property
    def status_code(self):
        return self.status

    @property
    def text(self):
        return self.data


class TestVisaOffers(TestCase):

    def setUp(self):
        self.visa = Visa()
        self.logger = logging.getLogger()
        self.orig_handlers = self.logger.handlers
        self.logger.handlers = []
        self.level = self.logger.level
        settings.TESTING = True

        self.card_info_add = [{
            'id': 1,
            'payment_token': '1111111111111111111112',
            'card_token': '111111111111112',
            'partner_slug': 'test_slug',
            'action_code': ActionCode.ADD,
            'date': 1475920002
        }, {
            'id': 2,
            'payment_token': '1111111111111111111113',
            'card_token': '111111111111113',
            'partner_slug': 'test_slug',
            'action_code': ActionCode.ADD,
            'date': 1475920002
        }]
        self.visa_success_response = json.dumps(
            {
                "userDetails":
                {
                    "externalUserId": "a74hd93d9812wir0174mk093dkie1",
                    "communityCode": "BINKCTE01",
                    "userId": "809902ef-3c0b-40b8-93bf-63e2621df06f",
                    "userKey": "a74hd93d9812wir0174mk093dkie1",
                    "languageId": "en-US",
                    "timeZoneId": "Pacific Standard Time",
                    "timeZoneShortCode": "PST",
                    "cards": [{
                        "cardId": "bfc33c1d-d4ef-e111-8d48-001a4bcdeef4",
                        "cardLast4": "1111",
                        "productId": "A",
                        "productIdDescription": "Visa Traditional",
                        "productTypeCategory": "Credit",
                        "cardStatus": "New"
                    }],
                    "userStatus": 1,
                    "enrollDateTime": "2020-01-29T15:02:55.067"
                },
                "correlationId": "ce708e6a-fd5f-48cc-b9ff-ce518a6fda1a",
                "responseDateTime": "2020-01-29T15:02:55.1860039Z",
                "responseStatus":
                {
                    "code": "SUCCESS",
                    "message": "Request proceed successfully without error.",
                    "responseStatusDetails": []
                }
            })

        # WARNING This is an estimate of a failed message which will need refinement
        # if more in depth testing is required
        self.visa_fail_response = json.dumps(
            {
                "userDetails":
                    {
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
                "responseStatus":
                    {
                        "code": "FAILED",
                        "message": "Request failed with error.",
                        "responseStatusDetails": []
                    }
            })

    def get_expected_add_response(self, uid, index=0):
        card = self.card_info_add[index]
        payment_token = card['payment_token']
        # This structure is defined in:
        # "https://hellobink.atlassian.net/wiki/spaces/ARCH/pages/934019468/Flows+-+Enrollment
        # The actual results will be compared
        result = {
            "delivery": {
                "payment_method_token": f"{payment_token}",
                "url": "https://api.visa.com/vop/v1/users/enroll",
                "headers": "Content-Type: application/json",
                "body": '{'
                        f'"correlationId": "{uid}",'
                        '"userDetails": {"communityCode": "BINKCTE01",'
                        f'"userKey": "{payment_token}",'
                        f'"externalUserId": "{payment_token}",'
                        '"cards": [{"cardNumber": "{{credit_card_number}}"}]'
                        '},'
                        '"communityTermsVersion": "1"}'
            }
        }
        return result

    @mock.patch('app.agents.visa_offers.uuid4')
    def test_add_card_body(self, mock_uuid):
        test_uuid = "ce708e6a-fd5f-48cc-b9ff-ce518a6fda1a"
        mock_uuid.return_value = test_uuid
        for i in range(0, 2):
            result = self.visa.add_card_body(self.card_info_add[i])
            expected_result = self.get_expected_add_response(test_uuid, i)
            result_dict = json.loads(result)
            result_dict_body = result_dict['delivery']['body']
            del(result_dict['delivery']['body'])
            expected_result_body = expected_result['delivery']['body']
            del(expected_result['delivery']['body'])

            # Check spreedly structure matches
            self.assertDictEqual(expected_result, result_dict)

            # Check visa body parts match when converted to json
            expected = json.loads(expected_result_body)
            actual = json.loads(result_dict_body)
            self.assertDictEqual(expected, actual)

            # repeat with a real uuid and different data
            test_uuid = str(uuid4())
            mock_uuid.return_value = test_uuid

    def test_response_handler_success_no_map(self):
        status_mapping = {}
        expected_status_code = 200
        response = ResponseMock(self.visa_success_response, expected_status_code)
        resp = self.visa.response_handler(response, "Add", status_mapping)
        self.assertEqual(expected_status_code, resp['status_code'])
        self.assertTrue("a74hd93d9812wir0174mk093dkie1" in resp['message'])
        self.assertTrue("successful" in resp['message'])
        self.assertEqual("", resp['bink_status'])

    def test_response_handler_success(self):
        status_mapping = {'BINK_UNKNOWN': "1"}
        expected_status_code = 200
        response = ResponseMock(self.visa_success_response, expected_status_code)
        resp = self.visa.response_handler(response, "Add", status_mapping)
        self.assertEqual(expected_status_code, resp['status_code'])
        self.assertTrue("a74hd93d9812wir0174mk093dkie1" in resp['message'])
        self.assertTrue("successful" in resp['message'])
        self.assertEqual("1", resp['bink_status'])

    def test_response_handler_404(self):
        status_mapping = {'BINK_UNKNOWN': "1"}
        expected_status_code = 404
        response = ResponseMock(self.visa_fail_response, expected_status_code)
        resp = self.visa.response_handler(response, "Add", status_mapping)
        self.assertEqual(expected_status_code, resp['status_code'])

    @httpretty.activate
    def test_un_enrol_success(self):
        visa = Visa()
        httpretty.register_uri(
            httpretty.POST,
            f"{visa.vop_url}{visa.vop_unenroll}",
            body='{"responseStatus":{"code": "SUCCESS","message": "unenrol success","responseStatusDetails": []}}'
        )
        card_info = self.card_info_add[0]
        card_info['action_code'] = ActionCode.DELETE
        card_info['partner_slug'] = "visa"
        result = remove_card(card_info)
        self.assertDictEqual(result, {'response_status': 'Success', 'status_code': 201})

    @httpretty.activate
    @mock.patch('app.services.put_account_status')
    def test_un_enrol_fail(self, mock_post):
        visa = Visa()
        httpretty.register_uri(
            httpretty.POST,
            f"{visa.vop_url}{visa.vop_unenroll}",
            body='{"responseStatus":{"code": "1000","message": "unenrol failure message","responseStatusDetails": []}}'
        )
        httpretty.register_uri(
            httpretty.GET,
            f"{HERMES_URL}/payment_cards/provider_status_mappings/visa",
            body='[{"provider_status_code": "Delete:1000" ,"bink_status_code": 10}]'
        )
        card_info = self.card_info_add[0]
        card_info['action_code'] = ActionCode.DELETE
        card_info['partner_slug'] = "visa"
        result = remove_card(card_info)
        self.assertDictEqual(result, {'response_status': 'Failed', 'status_code': 200})
        mock_post.assert_called_with(10, card_id=1, response_status='Failed')

    def tearDown(self):
        self.logger.handlers = self.orig_handlers
        self.logger.level = self.level
        settings.TESTING = False
