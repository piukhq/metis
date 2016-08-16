import arrow
import settings
import json
from io import StringIO


testing_hostname = 'http://latestserver.com/post.php'
testing_receiver_token = 'aDwu4ykovZVe7Gpto3rHkYWI5wI'
testing_create_url = 'https://test.api.loyaltyangels.com/file_enroll'
testing_remove_url = 'https://test.api.loyaltyangels.com/file_unenroll'
production_receiver_token = ''
production_create_url = 'test.api.loyaltyangels.com/file_enroll'


# ToDo work out the Visa file format and layout - code the request_body
class Visa:
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

    def request_body(self, card_info):
        recipient_id = 'nawes@visa.com'
        action_code = 'A'

        data = {
            "export": {
                "payment_method_tokens": ["LyWyubSnJzQZtAxLvN8RYOYnSKv"],
                "payment_method_data": {
                    "LyWyubSnJzQZtAxLvN8RYOYnSKv": {
                        "external_cardholder_id": "1111111111111111111111111",
                        "action_code": action_code
                    }
                },
                "callback_url": "https://api.chingrewards.com/payment_service/notify/spreedly",
                "url": "sftp://sftp.bink.com/file_test_8August2016_1.txt",
                "body": self.create_file_data(card_info)
            }
        }

        body_data = '{{#gpg}}' + self.visa_pem() + recipient_id + json.dumps(data) + '{{/gpg}}'
        return body_data

    def payment_method_data(self, card_info):
        """Construct the payment method data rows required for Spreedly
        to process the card_ids and add PAN's. Two tokens are required for Visa.
        Payment method token, Spreedly's token - Used by Spreedly to associate the PAN.
        External Cardholder ID, required for Visa, shorter token length, used for Transaction ID's"""
        payment_data = [{
                card['payment_token']: {
                    'external_cardholder_id': card['card_token'],
                    'action_code': card['action_code']
                }} for card in card_info]
        return payment_data

    def create_file_data(self, card_info):
        detail_record_count = len(card_info)
        header = Header(
            source_id='XXXX',
            destination_id='VISA',
            file_description='Some text here',
            file_create_date=self.format_datetime(arrow.now()),
            file_format_version='2.0',
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
                    promotion_type='XX',
                    promotion_code='XXXX',
                    action_code='{{action_code}}',
                    endpoint_code='XXXXXX',
                    promotion_group_id='XXXXXX',
                    cardholder_account_number='{{credit_card_number}}',
                    external_cardholder_id='{{external_cardholder_id}}',
                    effective_date='{{credit_card_created_at}}',
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
        ('file_format_version', 4, 'V'),
        ('test_file_indicator', 1, 'F'),
        ('filler1', 2, 'F'),
        ('filler2', 25, 'F'),
        ('file_type_indicator', 1, 'F'),
        ('file_unique_text', 20, 'V'),
        ('filler3', 650, 'F')
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
        ('cardholder_account_number', 19, 'P'),
        ('external_cardholder_id', 25, 'P'),
        ('effective_date', 8, 'D'),
        ('termination_date', 8, 'F'),
        ('filler', 712, 'F'),
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
        ('filler', 986, 'F'),
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
                start_str = '{{#format_text}}%-{0}.{1},'.format(item[1], item[1])
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
        end_str = '{{/format_text}}'
        self.footer_string = '{}{}{}'.format(start_str, serialized_str, end_str)

    def add_detail_start(self):
        """
        add a detail record start marker to the file
        :return: None
        """
        start_str = '{{#payment_methods}}{{#format_text}}%-1000.1000s,'
        self.details.append({'detail': start_str})

    def add_detail_end(self):
        """
        add a detail record end marker to the file
        :return: None
        """
        end_str = '{{/payment_methods}}{{/format_text}}'
        self.details.append({'detail': end_str})

    def add_detail(self, detail):
        """
        add a detail record to the file
        :param detail: the detail to add
        :return: None
        """

        self.details.append({
            'detail': self._serialize(Detail, detail),
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
        return '\n'.join(file_contents)
