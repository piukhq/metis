import arrow
import settings
import json
import time
from io import StringIO
from lxml import etree
from app.celery import sentry

production_receiver_token = 'HwA3Nr2SGNEwBWISKzmNZfkHl6D'
production_create_url = ''
production_remove_url = ''

testing_hostname = 'http://latestserver.com/post.php'
testing_receiver_token = '256eVeJ1hYZF35RdrA8WDcJ1h0F'
testing_create_url = ''
testing_remove_url = ''


class Visa:
    header = {'Content-Type': 'application/json'}

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
        return receiver_token + '/export.json'

    def request_header(self):
        header = '![CDATA[Content-Type: application/json]]'
        return header

    def response_handler(self, response, action):
        date_now = arrow.now()
        if response.status_code >= 300:
            resp_content = response.json()
            psp_message = resp_content['errors'][0]['message']
            message = 'Problem connecting to PSP. Action: Visa {}. Error:{}'.format(action, psp_message)
            sentry.captureMessage(message)
            return {'message': message, 'status_code': response.status_code}

        try:
            xml_doc = etree.fromstring(response.text)
            payment_method_token = xml_doc.xpath("//payment_method/token")
            string_elem = xml_doc.xpath("//body")[0].text
            visa_data = json.loads(string_elem)
        except Exception as e:
            message = str({'Visa {} Problem processing response. Exception: {}'.format(action, e)})
            resp = {'message': message, 'status_code': 422}
            sentry.captureMessage(message)

        if visa_data["status"] == "Failure":
            # Not a good news response.
            message = "{} Visa {} unsuccessful - Token:{}".format(date_now, action, payment_method_token[0].text)
            settings.logger.info(message)
            resp = {'message': 'Visa Fault recorded for ' + action, 'status_code': 422}
            sentry.captureMessage(message)
        else:
            # could be a good response
            message = "{} Visa {} successful - Token:{}, {}".format(date_now,
                                                                    action,
                                                                    payment_method_token[0].text,
                                                                    "Check Handback file")
            settings.logger.info(message)
            resp = {'message': action + ' Successful', 'status_code': 200}

        return resp

    def request_body(self, card_info, action_code):
        recipient_id = 'nawes@visa.com'

        body_data = '{{#gpg}}'+self.visa_pem()+","+recipient_id+","+self.create_file_data(card_info)+'{{/gpg}}'
        # body_data = self.visa_pem()+","+recipient_id+","+self.create_file_data(card_info)
        file_url = "sftp://sftp.bink.com/LOYANG_REG_PAN_{}{}".format(str(int(time.time())), '.gpg')
        data = {
            "export": {
                "payment_method_tokens": [card_info[0]['payment_token']],
                "payment_method_data": {
                    card_info[0]['payment_token']: {
                        "external_cardholder_id": card_info[0]['card_token'],
                        "action_code": action_code
                    }
                },
                "callback_url": "https://api.chingrewards.com/payment_service/notify/spreedly",
                "url": file_url,
                "body": "**body**"  # body_data
            }
        }

        json_data = json.dumps(data)
        json_data = json_data.replace("**body**", body_data)
        return json_data

    def add_card_body(self, card_info):
        action_code = 'A'
        request_data = self.request_body(card_info, action_code)
        return request_data

    def remove_card_body(self, card_info):
        action_code = 'D'
        request_data = self.request_body(card_info, action_code)
        return request_data

    def payment_method_data(self, card_info, action_code):
        """Construct the payment method data rows required for Spreedly
        to process the card_ids and add PAN's. Two tokens are required for Visa.
        Payment method token, Spreedly's token - Used by Spreedly to associate the PAN.
        External Cardholder ID, required for Visa, shorter token length, used for Transaction ID's"""
        payment_data = [{
                card['payment_token']: {
                    'external_cardholder_id': card['card_token'],
                    'action_code': action_code
                }} for card in card_info]
        return payment_data

    def create_file_data(self, card_info):
        detail_record_count = len(card_info)
        header = Header(
            source_id='LOYANG',
            destination_id='VISA',
            file_description='Bink user card registration information',
            file_create_date=self.format_datetime(arrow.now()),
            file_control_number='00',
            file_format_version='2.0',
            not_used1='',
            not_used2='',
            filler1='',
            filler2='',
            file_type_indicator='I',
            file_unique_text='Bink user card data',
            filler3=''
        )

        footer = Footer(
            record_count=str(detail_record_count).rjust(10, '0'),
            filler=''
        )

        file = VisaCardFile()
        file.set_header(header)
        file.set_footer(footer)

        # Need to add a start and end markers for Spreedly.
        file.add_detail_start()
        for card in card_info:
            file.add_detail(
                Detail(
                    promotion_type='VD',
                    promotion_code='3GB16LOYANPVLOYANGSAUG16A',
                    action_code='{{action_code}}',
                    endpoint_code='LOYANG',
                    promotion_group_id='LOYANG',
                    cardholder_account_number='{{credit_card_number}}',
                    external_cardholder_id='{{external_cardholder_id}}',
                    effective_date=self.format_datetime(arrow.now()),
                    termination_date='',
                    filler=''
                ),
            )
        file.add_detail_end()

        output_file = StringIO(file.freeze())
        temp = output_file.getvalue()
        output_file.close()

        return temp

    @staticmethod
    def format_datetime(date_time):
        """
        formats an <arrow> datetime into the format expected by Visa
        :param date_time: the <arrow> datetime to be formatted
        :return: a datetime string in the format 'YYYYMMDD'
        """
        return date_time.format('YYYYMMDD')

    @staticmethod
    def visa_pem():
        # This is Visa's public key required for encrypting the file contents
        pem = """-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: IPWorks! OpenPGP v9.0
xsBNBFdaDS0BCACPTH1Td1PSUSMeaTDAagncwV18KrpuXSPXWjTgPy9SLHeoKQDt
wxWlIoisyxV1Ex2LQZnidINgNCFzMi26+SqYucm6OFv2bllr91tpk8I0+aeL/XBC
J5DUEbG9JAMyegMyzTz9PjRu4peXV/IUf2/uBJifZyv1bBaARCBXBaHvv+qfJbHx
88QNVo5J7KU8C7MD8hqLxwtqDjHgKtXHGbyscMzJn+ySTueemqhOBI3jst/z9uL2
OuSXeO0DudcLsmp6bVrh3SqpLKiZMbj2GsNcwVA/ikJiriaXOESv2RI/h1j5MjRs
sg9tyJYytuDsqz/rEOVDnqfP5/xpiTX223tjABEBAAHNJHNmaWxlMi1sYS10YXFj
LVBST0QgPG5hd2VzQHZpc2EuY29tPsLAdAQTAQIAHgUCV1oNLwMLAgIEFQoIAgUW
AQIDAAIeAQIXgAIbDwAKCRBPCXevH0QlBoxhB/4o7sG1TOZlxjv9fuK1/Bx9ZjPJ
6zCWGEAMV3li/jDmiNfJUaJOL5ZV8ffLRhgvS6bvKlpdMaRY8FXuJQThGe4T/BU4
HJIP8jPR+x4CHoUHNw1rOVitdkc9y/tWoF7aYAWqcqBBQwqjH9XbSC2XcYbULcl8
j8rVVTbXvJIdnx7u6v9OOeyc6XO7AupV7zjQHE6bdDPnmhyM9Yf+1OkDxuGNywsv
0WP8iB847/ZPmaENvOofIsrbncbztgZu1V2fOJM6JRp0EbctSxP44Mk1K8AKcmx2
MFqkPdKpeZh2bO269TO8fMy82gx6ltzMtms2NrRL3NOWj6suLke7s8K8++JC
=Zp6G
-----END PGP PUBLIC KEY BLOCK-----""".replace('\n', r'\n')
        return pem


class Field(object):
    def __init__(self, **kwargs):
        if 'record_identifier' in kwargs:
            raise TypeError('you may not specify record_identifier in kwargs')
        for k, v in kwargs.items():
            setattr(self, k, v)


class Header(Field):
    fields = [
        ('record_type', 2, 'F'),
        ('record_sub_type', 2, 'F'),
        ('source_id', 6, 'F'),
        ('destination_id', 6, 'F'),
        ('file_description', 255, 'V'),
        ('file_create_date', 8, 'F'),
        ('file_control_number', 2, 'V'),
        ('file_format_version', 4, 'V'),
        ('test_file_indicator', 1, 'F'),
        ('not_used1', 8, 'V'),
        ('not_used2', 8, 'V'),
        ('filler1', 2, 'V'),
        ('filler2', 25, 'V'),
        ('file_type_indicator', 1, 'F'),
        ('file_unique_text', 20, 'V'),
        ('filler3', 650, 'V')
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.record_type = '00'
        self.record_sub_type = '00'
        if not settings.TESTING:
            self.test_file_indicator = 'P'
        else:
            self.test_file_indicator = 'T'


class Detail(Field):
    """
    F = Fixed value
    V = Variable value
    P = Parameter - Spreedly to Populate
    D = Date formatted value
    """
    fields = [
        ('record_type', 2, 'F'),
        ('record_sub_type', 2, 'F'),
        ('promotion_type', 2, 'F'),
        ('promotion_code', 25, 'F'),
        ('action_code', 1, 'P'),
        ('endpoint_code', 6, 'F'),
        ('promotion_group_id', 6, 'F'),
        ('cardholder_account_number', 19, 'V'),
        ('external_cardholder_id', 25, 'P'),
        ('effective_date', 8, 'D'),
        ('termination_date', 8, 'F'),
        ('filler', 896, 'V'),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.record_type = '10'
        self.record_sub_type = '01'


class Footer(Field):
    fields = [
        ('record_type', 2, 'F'),
        ('record_sub_type', 2, 'F'),
        ('record_count', 10, 'F'),
        ('filler', 986, 'V'),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.record_type = '99'
        self.record_sub_type = '99'


class VisaCardFile(object):

    def __init__(self):
        self.header_string = ''
        self.details = []
        self.footer_string = ''

    @staticmethod
    def _serialize(field_class, fields):
        """
        turns a given field into a string using field_class to choose the fields
        F = Fixed value
        V = Variable value
        P = Parameter - Spreedly to Populate
        :param field_class: a class deriving from Field
        :param fields: an instance of field_class
        :return: the serialized string
        """
        data = []
        for item in field_class.fields:
            if item[2] == 'F':
                data.append(str(getattr(fields, item[0])).ljust(item[1]))
            elif item[2] == 'P':
                data.append(str(getattr(fields, item[0])))
            elif item[2] == 'V':
                str_data = str(getattr(fields, item[0]))
                start_str = '{0}%-{1}.{2}s,'.format('{{#format_text}}', item[1], item[1])
                end_str = '{{/format_text}}'
                complete_str = start_str + str_data + end_str
                data.append(complete_str)
            elif item[2] == 'D':
                str_data = str(getattr(fields, item[0]))
                start_str = '{{#format_date}}%Y%m%d,'
                end_str = '{{/format_date}}'
                complete_str = start_str + str_data + end_str
                data.append(complete_str)

        return ''.join(data)

    def set_header(self, header):
        """
        set the header record for the file
        :param header: the header to use
        :return: None
        """
        serialized_str = self._serialize(Header, header)
        start_str = '{{#format_text}}%-1000.1000s,'
        end_str = '{{/format_text}}'
        self.header_string = '{}{}{}'.format(start_str, serialized_str, end_str)

    def set_footer(self, footer):
        """
        set the footer record for the file
        :param footer: the footer to use
        :return: None
        """
        serialized_str = self._serialize(Footer, footer)
        start_str = '{{#format_text}}%-1000.1000s,'
        end_str = '{{/format_text}}\\n'
        self.footer_string = '{}{}{}'.format(start_str, serialized_str, end_str)

    def add_detail_start(self):
        """
        add a detail record start marker to the file
        :return: None
        """
        start_str = '{{#payment_methods}}'
        self.details.append({'detail': start_str})

    def add_detail_end(self):
        """
        add a detail record end marker to the file
        :return: None
        """
        end_str = '{{/payment_methods}}'
        self.details.append({'detail': end_str})

    def add_detail(self, detail):
        """
        add a detail record to the file
        :param detail: the detail to add
        :return: None
        """
        start_str = '{{#format_text}}%-1000.1000s,'
        end_str = '{{/format_text}}'

        self.details.append({
            'detail': start_str + self._serialize(Detail, detail) + end_str,
        })

    def freeze(self):
        """
        freeze the current file contents into a string
        :return: a string representing the current state of the file
        """
        file_contents = [self.header_string]
        for detail in self.details:
            file_contents.append(detail['detail'])
        file_contents.append(self.footer_string)
        return '\\n'.join(file_contents)
