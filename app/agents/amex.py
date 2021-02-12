import base64
import hashlib
import hmac
import json
import random
import time

from lxml import etree

import settings

'''E2: https://api.qa.americanexpress.com/v2/datapartnership/offers/sync
E3: https://apigateway.americanexpress.com/v2/datapartnership/offers/sync'''
'''Amex use sync to add cards and unsync to remove cards from transactions output'''


port = "443"
res_path_sync = "/marketing/v4/smartoffers/card_accounts/cards/sync_details"
res_path_unsync = "/marketing/v4/smartoffers/card_accounts/cards/unsync_details"


class Amex:
    header = {'Content-Type': 'application/xml'}
    partnerId = 'AADP0050'
    distrChan = '9999'  # 'Amex to provide'
    receiver_function_open = "{{#base64}}{{#bytes_hex}}{{#hmac}}sha256,"
    receiver_function_close = "{{/hmac}}{{/bytes_hex}}{{/base64}}"

    def __init__(self):
        # Amex OAuth details
        self.client_id = settings.Secrets.amex_client_id
        self.client_secret = settings.Secrets.amex_client_secret
        self.rec_token = f"{settings.Secrets.spreedly_amex_receive_token}/deliver.xml"
        if settings.TESTING:
            self.url = settings.STUBBED_AMEX_URL
        else:
            # Production
            self.url = 'https://api.americanexpress.com'

    def add_url(self):
        return '{}{}'.format(self.url, res_path_sync)

    def remove_url(self):
        return '{}{}'.format(self.url, res_path_unsync)

    def receiver_token(self):
        return self.rec_token

    def request_header(self, res_path, req_body):
        mac_header = self.mac_api_header(res_path, req_body)
        auth = f'Authorization: "{mac_header}"'
        content_type = "Content-Type: application/json"
        api_key = f"X-AMEX-API-KEY: {self.client_id}"

        header = f"<![CDATA[{content_type}\n{auth}\n{api_key}]]>"
        return header

    def response_handler(self, response, action, status_mapping):
        if response.status_code >= 300:
            try:
                resp_content = response.json()
                psp_message = resp_content['errors'][0]['message']
            except ValueError:
                psp_message = 'Could not access the PSP receiver.'

            message = 'Problem connecting to PSP. Action: Amex {}. Error:{}'.format(action, psp_message)
            settings.logger.error(message)
            return {'message': message, 'status_code': response.status_code}

        try:
            xml_doc = etree.fromstring(response.text)
            payment_method_token = xml_doc.xpath("//payment_method/token")
            string_elem = xml_doc.xpath("//body")[0].text
            amex_data = json.loads(string_elem)
        except Exception:
            message = str({'Amex {} problem processing response.'.format(action)})
            resp = {'message': message, 'status_code': 422}
            settings.logger.error(message, exc_info=1)
        else:
            if amex_data["status"] == "Failure":
                # Not a good news response.
                message = "Amex {} unsuccessful - Token: {}, {}, {} {}".format(action,
                                                                               payment_method_token[0].text,
                                                                               amex_data["respDesc"],
                                                                               "Code:",
                                                                               amex_data["respCd"])
                settings.logger.info(message)
                resp = {'message': action + ' Amex fault recorded. Code: ' + amex_data["respCd"], 'status_code': 422}
            else:
                # could be a good response
                message = "Amex {} successful - Token: {}, {}".format(action,
                                                                      payment_method_token[0].text,
                                                                      "Amex successfully processed")
                settings.logger.info(message)

                resp = {'message': message, 'status_code': 200}

            if amex_data and amex_data['respCd'] in status_mapping:
                resp['bink_status'] = status_mapping[amex_data['respCd']]
            else:
                resp['bink_status'] = status_mapping['BINK_UNKNOWN']

        return resp

    def add_card_request_body(self, card_id):
        msg_id = str(int(time.time()))  # 'Can this be a guid or similar?'
        data = {
            "msgId": msg_id,
            "partnerId": self.partnerId,
            "cardNbr": "{{credit_card_number}}",
            "cmAlias1": card_id['payment_token'],
            "distrChan": self.distrChan
        }
        body_data = f"<![CDATA[{json.dumps(data)}]]>"
        return body_data

    def remove_card_request_body(self, card_id):
        msg_id = str(int(time.time()))  # 'Can this be a guid or similar?'
        data = {
            "msgId": msg_id,
            "partnerId": self.partnerId,
            "cmAlias1": card_id['payment_token'],
            "distrChan": self.distrChan
        }
        body_data = f"<![CDATA[{json.dumps(data)}]]>"
        return body_data

    def add_card_body(self, card_info):
        body = self.add_card_request_body(card_info)
        xml_data = '<delivery>' \
                   '  <payment_method_token>' + card_info['payment_token'] + '</payment_method_token>' \
                   '  <url>' + self.add_url() + '</url>' \
                   '  <headers>' + self.request_header(res_path_sync, body) + '</headers>' \
                   '  <body>' + body + '</body>' \
                   '</delivery>'
        return xml_data

    def remove_card_body(self, card_info):
        body = self.add_card_request_body(card_info)
        xml_data = '<delivery>' \
                   '  <payment_method_token>' + card_info['payment_token'] + '</payment_method_token>' \
                   '  <url>' + self.remove_url() + '</url>' \
                   '  <headers>' + self.request_header(res_path_unsync, body) + '</headers>' \
                   '  <body>' + body + '</body>' \
                   '</delivery>'
        return xml_data

    def remove_cdata(self, input_string):
        output_string1 = input_string.replace("<![CDATA[", "")
        output_string2 = output_string1.replace("]]>", "")
        output_string3 = output_string2.replace(",", ",")
        return output_string3

    def mac_api_header(self, res_path_in, req_body):
        """
        Authentication=”MAC id=” client id value”,
        ts=”time stamp generated by client(In unix epoch time format)”,
        nonce=”unique identifier string”,
        mac=”request MAC generated using HMAC SHA1 algorithm”
        i. Use HMAC SHA1 algorithm.
        ii. Base string constructed using below parameters with following order followed by newline
            a.  ts - timestamp
            b. nonce = ts:BINK
            c. HTTP Method = POST
            d. Resource path = '/v1/apis/getme' url encoded
            e. host = 'api.qa.americanexpress.com'
            f. post : 443
        iii. Use OAuth token as key.
        iv. Base 64 encoding on output raw data
        :return: mac token.
        """
        body_hash = self.remove_cdata(self.receiver_function_open + self.client_secret + "," + req_body +
                                      self.receiver_function_close)
        millis = int(round(time.time() * 1000))
        ts = millis
        random.seed(millis)
        post_fix = 10000000 + random.randint(0, 90000000)
        nonce = str(ts + post_fix) + ":AMEX"  # ":BINK"
        host = self.url.replace("https://", "")
        base_string = str(ts) + "\n" + nonce + "\n" + "POST\n" + res_path_in + "\n" + host + "\n" + port \
                      + "\n" + body_hash + "\n"
        mac = (self.receiver_function_open + self.client_secret + "," + base_string +
               self.receiver_function_close)
        auth_header = f'MAC id="{self.client_id}",ts="{str(ts)}",nonce="{nonce}",bodyhash="{body_hash}",mac="{mac}"'
        return auth_header


def generate_mac(encoded_base_string, secret):
    secret_key = secret.encode('utf-8')
    dig = hmac.new(secret_key, msg=encoded_base_string, digestmod=hashlib.sha256).digest()
    mac = str(base64.b64encode(dig), 'utf-8')
    return mac
