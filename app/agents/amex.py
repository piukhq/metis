import settings
import json
import datetime
import time

'''E2: https://api.qa.americanexpress.com/v2/datapartnership/offers/sync
E3: https://apigateway.americanexpress.com/v2/datapartnership/offers/sync'''
'''Amex use sync to add cards and unsync to remove cards from transactions output'''

testing_hostname = 'http://latestserver.com/post.php'
testing_receiver_token = 'aDwu4ykovZVe7Gpto3rHkYWI5wI'
testing_create_url = 'https://api.qa.americanexpress.com/v2/datapartnership/offers/sync'
testing_remove_url = 'https://api.qa.americanexpress.com/v2/datapartnership/offers/unsync'
production_receiver_token = ''
production_create_url = 'https://apigateway.americanexpress.com/v2/datapartnership/offers/sync'


class Amex:
    def url(self):
        if not settings.TESTING:
            service_url = production_create_url
        else:
            service_url = testing_create_url
        return service_url

    def receiver_token(self):
        if not settings.TESTING:
            receiver_token = production_receiver_token
        else:
            receiver_token = testing_receiver_token
        return receiver_token

    def request_header(self):
        header = '![CDATA[Content-Type: application/json]]'
        return header

    def request_body(self):
        msgId = time.mktime(datetime.datetime.now().timetuple())  # 'Can this be a guid or similar?'
        partnerId = 'Amex to provide'
        cmAlias1 = 'card_id_token'
        distrChan = 'Amex to provide'

        data = {
            "msgId": msgId,
            "partnerId": partnerId,
            "cardNbr": "{{credit_card_number}}",
            "cmAlias1": cmAlias1,
            "distrChan": distrChan
        }
        # Todo - check if "langCd": "en", "ctryCd": "US", required

        body_data = '![CDATA[{' + json.dumps(data) + '}]]'
        return body_data
