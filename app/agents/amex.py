import random
import settings
import json
import time
import hmac
import hashlib
import base64
import requests
from urllib import parse
from lxml import etree

'''E2: https://api.qa.americanexpress.com/v2/datapartnership/offers/sync
E3: https://apigateway.americanexpress.com/v2/datapartnership/offers/sync'''
'''Amex use sync to add cards and unsync to remove cards from transactions output'''

testing_receiver_token = 'BqfFb1WnOwpbzH7WVTqmvYtffPV'
host = "api.qa.americanexpress.com"
port = "443"
testing_create_url = 'https://api.qa.americanexpress.com/v3/smartoffers/sync'
testing_remove_url = 'https://api.qa.americanexpress.com/v3/smartoffers/unsync'
production_receiver_token = 'ZQLPEvBP4jaaYhxHDl7SWobMXDt'
production_create_url = 'https://api.qa.americanexpress.com/v3/smartoffers/sync'
production_remove_url = 'https://api.qa.americanexpress.com/v3/smartoffers/unsync'

# Amex OAuth details
client_id = "e0e1114e-b63d-4e72-882b-29ad364573ac"
client_secret = "a44bfb98-239c-4ac0-85ae-685ed110e3af"


class Amex:
    header = {'Content-Type': 'application/xml'}
    partnerId = 'AADP0050'  # 'Amex to provide'
    distrChan = '9999'  # 'Amex to provide'

    def add_url(self):
        if not settings.TESTING:
            service_url = production_create_url
        else:
            service_url = testing_create_url
        return service_url

    def remove_url(self):
        if not settings.TESTING:
            service_url = production_remove_url
        else:
            service_url = testing_remove_url
        return service_url

    def receiver_token(self):
        if not settings.TESTING:
            receiver_token = production_receiver_token
        else:
            receiver_token = testing_receiver_token
        return receiver_token + '/deliver.xml'

    def request_header(self, resPath):
        header_start = '<![CDATA['
        content_type = 'Content-Type: application/json'
        auth_header = mac_auth_header()
        oauth_resp = self.amex_oauth(auth_header)

        access_token = oauth_resp['access_token']
        mac_key = oauth_resp['mac_key']
        mac_header = mac_api_header(access_token, mac_key, resPath)
        authentication = 'Authorization: ' + "\"" + mac_header + "\""

        api_key = 'X-AMEX-API-KEY: {}'.format(client_id)
        access_key = 'X-AMEX-ACCESS-KEY: {}'.format(access_token)
        header_end = ']]>'

        header = "{0}{1}\n{2}\n{3}\n{4}{5}".format(header_start, content_type, authentication,
                                                   api_key, access_key, header_end)
        return header

    def response_handler(self, response):
        if response.status_code != 200:
            return {'message': 'Amex Unknown error', 'status_code': response.status_code}

        try:
            xml_doc = etree.fromstring(response.text)
            payment_method_token = xml_doc.xpath("//payment_method/token")
            string_elem = xml_doc.xpath("//body")[0].text
            amex_data = json.loads(string_elem)

            if amex_data["status"] == "Failure":
                # Not a good news response.
                message = "Amex Process unsuccessful - Token:{}, {}, {} {}".format(payment_method_token[0].text,
                                                                                   amex_data["respDesc"],
                                                                                   "Code:",
                                                                                   amex_data["respCd"])
                settings.logger.info(message)
                resp = {'message': 'Amex Fault recorded. Code: ' + amex_data["respCd"], 'status_code': 422}
            else:
                # could be a good response
                message = "Amex Process successful - Token:{}, {}".format(payment_method_token[0].text,
                                                                          "Amex successfully registered")
                settings.logger.info(message)
                resp = {'message': 'Successful', 'status_code': 200}
        except Exception as e:
            message = str({'Amex Problem processing response. Exception: {}'.format(e)})
            resp = {'message': message, 'status_code': 422}

        return resp

    def add_card_request_body(self, card_ids):
        msgId = str(int(time.time()))  # 'Can this be a guid or similar?'

        data = {
            "msgId": msgId,
            "partnerId": self.partnerId,
            "cardNbr": "{{credit_card_number}}",
            "cmAlias1": card_ids[0]['payment_token'],
            "distrChan": self.distrChan
        }

        body_data = '<![CDATA[' + json.dumps(data) + ']]>'
        return body_data

    def remove_card_request_body(self, card_ids):
        msgId = str(int(time.time()))  # 'Can this be a guid or similar?'

        data = {
            "msgId": msgId,
            "partnerId": self.partnerId,
            "cardNbr": "{{credit_card_number}}",
            "cmAlias1": card_ids[0]['payment_token'],
            "distrChan": self.distrChan
        }

        body_data = '<![CDATA[' + json.dumps(data) + ']]>'
        return body_data

    def add_card_body(self, card_info):
        res_path = "/v3/smartoffers/sync"
        xml_data = '<delivery>' \
                   '  <payment_method_token>' + card_info[0]['payment_token'] + '</payment_method_token>' \
                   '  <url>' + self.add_url() + '</url>' \
                   '  <headers>' + self.request_header(res_path) + '</headers>' \
                   '  <body>' + self.add_card_request_body(card_info) + '</body>' \
                   '</delivery>'
        return xml_data

    def remove_card_body(self, card_info):
        res_path = "/v3/smartoffers/unsync"
        xml_data = '<delivery>' \
                   '  <payment_method_token>' + card_info[0]['payment_token'] + '</payment_method_token>' \
                   '  <url>' + self.remove_url() + '</url>' \
                   '  <headers>' + self.request_header(res_path) + '</headers>' \
                   '  <body>' + self.remove_card_request_body(card_info) + '</body>' \
                   '</delivery>'
        return xml_data

    def amex_oauth(self, auth_header):
        # Call the Amex OAuth endpoint to obtain an API request token.
        base_url = "https://api.qa.americanexpress.com"
        auth_url = base_url + "/apiplatform/v2/oauth/token/mac"
        # payload = "grant_type=client_credentials&app_spec_info=Apigee&guid_type=privateguid&scope=ThanxSmartOffers_"
        payload = "grant_type=client_credentials&scope="

        header = {"Content-Type": "application/x-www-form-urlencoded",
                  "Authentication": auth_header,
                  "X-AMEX-API-KEY": client_id}

        resp = requests.post(auth_url, data=payload, headers=header)
        resp_json = json.loads(resp.content.decode())
        if resp.status_code == 200:
            return resp_json
        else:
            return None


def mac_auth_header():
    """
    Authentication=”MAC id=” client id value”,
    ts=”time stamp generated by client(In unix epoch time format)”,
    nonce=”unique identifier string”,
    mac=”request MAC generated using HMAC SHA1 algorithm”
    i. Use HMAC SHA1 algorithm.
    ii. Base string constructed using below parameters with following order followed by newline
        a.  client_id
        b. ts (timestamp in unix epoch format)
        c. nonce
        d. grant_type
    iii. Use client_secret as key.
    iv. Base 64 encoding on output raw data
    :return: mac token.
    """
    ts = str(int(time.time()))
    nonce = ts + ":AMEX"  # ":BINK"
    base_string = client_id + "\n" + ts + "\n" + nonce + "\n" + "client_credentials" + "\n"
    base_string_bytes = base_string.encode('utf-8')
    mac = generate_mac(base_string_bytes, client_secret)

    auth_header = "MAC id=\"" + client_id + "\",ts=\"" + ts + "\",nonce=\"" + nonce + "\",mac=\"" + mac + "\""

    return auth_header


def mac_api_header(access_token, mac_key, res_path_in):
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
    res_path = parse.quote(res_path_in, safe='')
    ts = int(time.time())
    millis = int(round(time.time() * 1000))
    random.seed(millis)
    post_fix = 10000000 + random.randint(0, 90000000)
    nonce = str(ts + post_fix) + ":AMEX"  # ":BINK"
    base_string = str(ts)+"\n"+nonce+"\n"+"POST\n"+res_path+"\n"+host+"\n"+port+"\n\n"
    base_string_bytes = base_string.encode('utf-8')
    mac = generate_mac(base_string_bytes, mac_key)

    auth_header = "MAC id=\"" + access_token + "\",ts=\"" + str(ts) + "\",nonce=\"" + nonce + "\",mac=\"" + mac + "\""

    return auth_header


def generate_mac(encoded_base_string, secret):
    secret_key = secret.encode('utf-8')
    dig = hmac.new(secret_key, msg=encoded_base_string, digestmod=hashlib.sha256).digest()
    mac = str(base64.b64encode(dig), 'utf-8')
    return mac
