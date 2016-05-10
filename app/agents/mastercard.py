import settings
from string import Template

testing_hostname = 'http://latestserver.com/post.php'
testing_receiver_token = 'aDwu4ykovZVe7Gpto3rHkYWI5wI'
testing_endpoint = 'https://ws.mastercard.com/mtf/MRS/CustomerService'
production_hostname = ''
production_receiver_token = ''
production_endpoint = 'https://ws.mastercard.com/MRS/CustomerService'


class MasterCard:
    def hostname(self):
        if not settings.TESTING:
            host_name = production_hostname
        else:
            host_name = testing_hostname
        return host_name

    def receiver_token(self):
        if not settings.TESTING:
            receiver_token = production_receiver_token
        else:
            receiver_token = testing_receiver_token
        return receiver_token

    def request_header(self):
        if not settings.TESTING:
            endpoint = production_endpoint
        else:
            endpoint = testing_endpoint

        header = '![CDATA[Content-Type: application/xml' \
                 'SOAPAction: ' + endpoint + ']]'
        return header

    def request_body(self):
        app_id = 'Get app id from MasterCard'
        bank_customer_number = 'get the token'
        member_ica = '17597'  # TODO check member ica
        bank_product_code = 'MRS code for card product provided by MC'
        program_identifier = 'MRS program id'

        request = Template(u"""<?xml version="1.0" encoding="utf-8"?>
                  <soapenv:envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:web="http://www.webserviceX.NET/">
                      <soapenv:header>
                      <identity>
                      <appID>$app_id</appID>
                      <institutionName> Loyalty Angels </institutionName>
                      </identity>
                      <soapenv:body>
                        <cus:enroll>
                            <cus:customerFields>
                                <cus:BANK_CUSTOMER_NUMBER>$bank_customer_number</cus:BANK_CUSTOMER_NUMBER>
                                <cus:MEMBER_ICA>$member_ica</cus:MEMBER_ICA>
                            </cus:customerFields>
                            <cus:customerAccountFields>
                                <cus:BANK_ACCOUNT_NUMBER>{{credit_card_number}}</cus:BANK_ACCOUNT_NUMBER>
                                <cus:ACCOUNT_STATUS_CODE>1</cus:ACCOUNT_STATUS_CODE>
                                <cus:BANK_PRODUCT_CODE>$bank_product_code</cus:BANK_PRODUCT_CODE>
                                <cus:PROGRAM_IDENTIFIER>$program_identifier</cus:PROGRAM_IDENTIFIER>
                            </cus:customerAccountFields>
                        </cus:enroll>
                      </soapenv:body>
                  </soapenv:header></soapenv:envelope>""")

        soap = request.substitute(app_id=app_id,
                           bank_customer_number=bank_customer_number,
                           member_ica=member_ica,
                           bank_product_code=bank_product_code,
                           program_identifier=program_identifier)

        body_data = '![CDATA[{' + soap + '}]]'
        return body_data
