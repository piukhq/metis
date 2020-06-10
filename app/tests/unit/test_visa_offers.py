import json
import logging
from unittest import mock
from flask.ext.testing import TestCase
from app import create_app
from uuid import uuid4

import httpretty
from settings import HERMES_URL
import settings
from app.agents.visa_offers import Visa
from app.card_router import ActionCode
from app.services import remove_card
from app.tasks import add_card as t_add_card, remove_card as t_remove_card, reactivate_card as t_reactivate_card

auth_key = 'Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL' \
           'CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU'


class Testing:
    TESTING = True


def mock_celery_handler(action_code, card_info):
    {ActionCode.ADD: lambda: t_add_card(card_info),
     ActionCode.DELETE: lambda: t_remove_card(card_info),
     ActionCode.REACTIVATE: lambda: t_reactivate_card(card_info)}[action_code]()


def mock_process_card(action_code, card_info):
    card_info['action_code'] = action_code
    mock_celery_handler(action_code, card_info)


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

    @classmethod
    def setUpClass(cls):
        settings.TESTING = True
        cls.visa = Visa()
        cls.vop_enrol_url = f"{cls.visa.vop_url}{cls.visa.vop_enrol}"
        cls.vop_un_enrol_url = f"{cls.visa.vop_url}{cls.visa.vop_unenroll}"
        cls.vop_activation_url = f"{cls.visa.vop_url}{cls.visa.vop_activation}"
        cls.vop_deactivation_url = f"{cls.visa.vop_url}{cls.visa.vop_deactivation}"
        cls.metis_activate_endpoint = "/visa/activate/"
        cls.metis_deactivate_endpoint = "/visa/deactivate/"
        cls.metis_payment_card_endpoint = "/payment_service/payment_card"

    def setUp(self):
        settings.TESTING = True
        self.logger = logging.getLogger()
        self.orig_handlers = self.logger.handlers
        self.logger.handlers = []
        self.level = self.logger.level
        self.call_count = 0

        self.card_info_add = [{
            'id': 1,
            'payment_token': '1111111111111111111112',
            'card_token': '111111111111112',
            'partner_slug': 'visa',
            'date': 1475920002
        }, {
            'id': 2,
            'payment_token': '1111111111111111111113',
            'card_token': '111111111111113',
            'partner_slug': 'visa',
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

    def create_app(self):
        return create_app(Testing)

    def get_expected_add_response(self, uid, index=0):
        card = self.card_info_add[index]
        payment_token = card['payment_token']
        visa = Visa()
        # This structure is defined in:
        # "https://hellobink.atlassian.net/wiki/spaces/ARCH/pages/934019468/Flows+-+Enrollment
        # The actual results will be compared
        result = {
            "delivery": {
                "payment_method_token": f"{payment_token}",
                "url": "https://cert.api.visa.com/vop/v1/users/enroll",
                "headers": visa.spreedly_vop_headers,
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

    @staticmethod
    def mock_status_mappings_call():
        httpretty.register_uri(
            httpretty.GET,
            f"{HERMES_URL}/payment_cards/provider_status_mappings/visa",
            body=json.dumps(
                [
                    {"provider_status_code": "Delete:1000", "bink_status_code": 10},
                    {"provider_status_code": "Delete:4000", "bink_status_code": 20}
                ]
            )
        )

    @staticmethod
    def retry_response(response_headers, code="4000"):
        return [200, response_headers, json.dumps(
            {
                "responseStatus": {
                    "code": code, "message": "un-enrol retry failure message", "responseStatusDetails": []
                }
            }
        )]

    @staticmethod
    def success_response(response_headers, code="SUCCESS"):
        return [200, response_headers, json.dumps(
            {
                "responseStatus": {
                    "code": code, "message": "un-enrol equivalent to success", "responseStatusDetails": []
                }
            }
        )]

    @staticmethod
    def fail_response(response_headers, code='1000'):
        return [200, response_headers, json.dumps(
            {
                "responseStatus": {
                     "code": code, "message": "un-enrol failure message", "responseStatusDetails": []
                }
            }
        )]

    def mock_vop_success_response(self, request, uri, response_headers):
        self.call_count += 1
        return self.success_response(response_headers)

    def mock_vop_fail_response(self, request, uri, response_headers):
        self.call_count += 1
        return self.fail_response(response_headers)

    def mock_vop_retry_response(self, request, uri, response_headers):
        self.call_count += 1
        return self.retry_response(response_headers)

    def mock_vop_fail_response_on_2nd_retry(self, request, uri, response_headers):
        self.call_count += 1
        if self.call_count != 2:
            return self.retry_response(response_headers)
        else:
            return self.fail_response(response_headers)

    def mock_vop_success_on_3rd_retry(self, request, uri, response_headers):
        self.call_count += 1
        if self.call_count != 3:
            return self.retry_response(response_headers)
        else:
            return self.success_response(response_headers, "RTMENRE0026")

    def un_enrol_remove_card_scenario(self, scenario):
        httpretty.register_uri(
            httpretty.POST,
            self.vop_un_enrol_url,
            body=scenario
        )
        self.mock_status_mappings_call()
        card_info = self.card_info_add[0]
        card_info['action_code'] = ActionCode.DELETE
        return remove_card(card_info)

    def un_enrol_scenario(self, scenario):
        httpretty.register_uri(
            httpretty.POST,
            self.vop_un_enrol_url,
            body=scenario
        )
        self.mock_status_mappings_call()
        card_info = self.card_info_add[0]
        resp = self.client.delete(self.metis_payment_card_endpoint,
                                  headers={'content-type': 'application/json', 'Authorization': auth_key},
                                  data=json.dumps(card_info))
        return resp

    def activate_scenario(self, scenario):
        httpretty.register_uri(
            httpretty.POST,
            self.vop_activation_url,
            body=scenario
        )
        card_info = self.card_info_add[0]
        resp = self.client.post(self.metis_activate_endpoint,
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps(card_info))
        return resp

    def deactivate_scenario(self, scenario):
        httpretty.register_uri(
            httpretty.POST,
            self.vop_deactivation_url,
            body=scenario
        )
        card_info = self.card_info_add[0]
        resp = self.client.post(self.metis_deactivate_endpoint,
                                headers={'content-type': 'application/json', 'Authorization': auth_key},
                                data=json.dumps(card_info))
        return resp

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
    def test_remove_card_success(self):
        result = self.un_enrol_remove_card_scenario(self.mock_vop_success_response)
        self.assertDictEqual(result, {'response_status': 'Success', 'status_code': 201})
        self.assertEqual(1, self.call_count, f"Error in retry logic")

    @httpretty.activate
    @mock.patch('app.services.put_account_status')
    def test_remove_card_fail(self, mock_post):
        result = self.un_enrol_remove_card_scenario(self.mock_vop_fail_response)
        self.assertDictEqual(result, {'response_status': 'Failed', 'status_code': 200})
        mock_post.assert_called_with(10, card_id=1, response_status='Failed')
        self.assertEqual(1, self.call_count, f"Error in retry logic")

    @httpretty.activate
    @mock.patch('app.services.put_account_status')
    def test_remove_card_retry(self, mock_post):
        result = self.un_enrol_remove_card_scenario(self.mock_vop_retry_response)
        self.assertDictEqual(result, {'response_status': 'Retry', 'status_code': 200})
        mock_post.assert_called_with(20, card_id=1, response_status='Retry')
        self.assertEqual(self.visa.MAX_RETRIES, self.call_count, f"Retry count should be {self.visa.MAX_RETRIES}")

    @httpretty.activate
    @mock.patch('app.services.put_account_status')
    def test_remove_card_retry_fail_on_2(self, mock_post):
        result = self.un_enrol_remove_card_scenario(self.mock_vop_fail_response_on_2nd_retry)
        self.assertDictEqual(result, {'response_status': 'Failed', 'status_code': 200})
        mock_post.assert_called_with(10, card_id=1, response_status='Failed')
        self.assertGreaterEqual(self.visa.MAX_RETRIES, 3, f"Retries is set to {self.visa.MAX_RETRIES};"
                                                          f" Must be >2 for this test to be valid ")
        self.assertEqual(2, self.call_count, f"Error in retry logic")

    @httpretty.activate
    @mock.patch('app.services.put_account_status')
    def test_remove_card_retry_success_on_3(self, mock_post):
        result = self.un_enrol_remove_card_scenario(self.mock_vop_success_on_3rd_retry)
        self.assertDictEqual(result, {'response_status': 'Success', 'status_code': 201})
        mock_post.assert_not_called()
        self.assertGreaterEqual(self.visa.MAX_RETRIES, 3, f"Retries is set to {self.visa.MAX_RETRIES};"
                                                          f" Must be >= 3 for this test to be valid ")
        self.assertEqual(3, self.call_count, f"Error in retry logic")

    @httpretty.activate
    def test_activate_success(self):
        resp = self.activate_scenario(self.mock_vop_success_response)
        self.assertEqual(resp.status_code, 201)
        self.assertDictEqual(resp.json, {'response_status': 'Success', 'agent_response_code': 'Activate:SUCCESS'})
        self.assertEqual(1, self.call_count, f"Error in retry logic")

    @httpretty.activate
    def test_activate_fail(self):
        resp = self.activate_scenario(self.mock_vop_fail_response)
        self.assertEqual(resp.status_code, 200)
        self.assertDictEqual(resp.json, {'response_status': 'Failed', 'agent_response_code': 'Activate:1000'})
        self.assertEqual(1, self.call_count, f"Error in retry logic")

    @httpretty.activate
    def test_activate_retry(self):
        resp = self.activate_scenario(self.mock_vop_retry_response)
        self.assertEqual(resp.status_code, 200)
        self.assertDictEqual(resp.json, {'response_status': 'Retry', 'agent_response_code': 'Activate:4000'})
        self.assertEqual(self.visa.MAX_RETRIES, self.call_count, f"Retry count should be {self.visa.MAX_RETRIES}")

    @httpretty.activate
    def test_deactivate_success(self):
        resp = self.deactivate_scenario(self.mock_vop_success_response)
        self.assertEqual(resp.status_code, 201)
        self.assertDictEqual(resp.json, {'response_status': 'Success', 'agent_response_code': 'Deactivate:SUCCESS'})
        self.assertEqual(1, self.call_count, f"Error in retry logic")

    @httpretty.activate
    def test_deactivate_fail(self):
        resp = self.deactivate_scenario(self.mock_vop_fail_response)
        self.assertEqual(resp.status_code, 200)
        self.assertDictEqual(resp.json, {'response_status': 'Failed', 'agent_response_code': 'Deactivate:1000'})
        self.assertEqual(1, self.call_count, f"Error in retry logic")

    @httpretty.activate
    def test_deactivate_retry(self):
        resp = self.deactivate_scenario(self.mock_vop_retry_response)
        self.assertEqual(resp.status_code, 200)
        self.assertDictEqual(resp.json, {'response_status': 'Retry', 'agent_response_code': 'Deactivate:4000'})
        self.assertEqual(self.visa.MAX_RETRIES, self.call_count, f"Retry count should be {self.visa.MAX_RETRIES}")

    @httpretty.activate
    @mock.patch('app.resources.process_card', side_effect=mock_process_card)
    @mock.patch('app.services.put_account_status')
    def test_unenrol_success(self, mock_post, _):
        resp = self.un_enrol_scenario(self.mock_vop_success_response)
        self.assertEqual(resp.status_code, 200)
        mock_post.assert_not_called()
        self.assertEqual(1, self.call_count, f"Error in retry logic")

    @httpretty.activate
    @mock.patch('app.resources.process_card', side_effect=mock_process_card)
    @mock.patch('app.services.put_account_status')
    def test_unenrol_fail(self, mock_post, _):
        resp = self.un_enrol_scenario(self.mock_vop_fail_response)
        self.assertEqual(resp.status_code, 200)
        mock_post.assert_called_with(10, card_id=1, response_status='Failed')
        self.assertEqual(1, self.call_count, f"Error in retry logic")

    @httpretty.activate
    @mock.patch('app.resources.process_card', side_effect=mock_process_card)
    @mock.patch('app.services.put_account_status')
    def test_unenrol_retry(self, mock_post, _):
        resp = self.un_enrol_scenario(self.mock_vop_retry_response)
        self.assertEqual(resp.status_code, 200)
        mock_post.assert_called_with(20, card_id=1, response_status='Retry')
        self.assertEqual(self.visa.MAX_RETRIES, self.call_count, f"Retry count should be {self.visa.MAX_RETRIES}")

    def tearDown(self):
        self.logger.handlers = self.orig_handlers
        self.logger.level = self.level
        settings.TESTING = False
