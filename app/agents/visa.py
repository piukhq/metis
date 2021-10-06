import arrow
import settings
import json
import time
import psycopg2

from io import StringIO

from app.action import ActionCode
from app.agents.agent_base import AgentBase
from app.hermes import put_account_status


class Visa(AgentBase):
    header = {'Content-Type': 'application/json'}

    def receiver_token(self):
        if settings.TESTING:
            return 'visa' + '/export.json'
        else:
            return 'HwA3Nr2SGNEwBWISKzmNZfkHl6D' + '/export.json'

    def request_header(self):
        header = '![CDATA[Content-Type: application/json]]'
        return header

    def response_handler(self, response):
        if response.status_code >= 300:
            try:
                resp_content = response.json()
                psp_message = resp_content['errors'][0]['message']
            except ValueError:
                psp_message = 'Could not access the PSP receiver.'

            message = 'Problem connecting to PSP. Action: Visa {}. Error:{}'.format('batch', psp_message)
            settings.logger.error(message)
            return

        try:
            psp_json = response.json()
            visa_data = psp_json['transaction']
        except Exception:
            message = 'Visa batch problem processing response.'
            settings.logger.error(message, exc_info=1)
            return

        if visa_data["state"] in ["pending", "succeeded"]:
            # could be a good response
            message = "Visa {} successful - Token: {}, {}".format('batch',
                                                                  visa_data['token'],
                                                                  "Check Handback file")
        else:
            # Not a good news response.
            message = "Visa {} unsuccessful - Transaction Token: {}".format('batch', visa_data['token'])

        settings.logger.info(message)

    def request_body(self, card_info):
        recipient_id = 'nawes@visa.com'

        body_data = '{{#gpg}}' + self.visa_pem() + "," + recipient_id + "," + \
            self.create_file_data(card_info) + '{{/gpg}}'
        file_name = "LOYANG_REG_PAN_{}{}".format(str(int(time.time())), '.gpg')
        file_url = "sftp://sftp.bink.com/{}".format(file_name)

        def get_visa_action_code(action_code):
            return {ActionCode.ADD: 'A',
                    ActionCode.DELETE: 'D'}[action_code]

        data = {
            "export": {
                "payment_method_tokens": [x['payment_token'] for x in card_info],
                "payment_method_data": {x['payment_token']: {
                    "external_cardholder_id": x['card_token'],
                    "action_code": get_visa_action_code(x['action_code']),
                    "effective_date": self.format_datetime(arrow.get(x['date']).to('Europe/London')),
                    "termination_date": self.set_termination_date(get_visa_action_code(x['action_code']))
                } for x in card_info},
                "callback_url": "https://api.chingrewards.com/payment_service/notify/spreedly",
                "url": file_url,
                "body": "**body**"  # body_data
            }
        }

        json_data = json.dumps(data)
        json_data = json_data.replace("**body**", body_data)
        return json_data, file_name

    def set_termination_date(self, action_code_in):
        if action_code_in == 'D':
            return self.format_datetime(arrow.now())
        else:
            return ''

    def create_cards(self, card_info):
        """Once the receiver has been created and token sent back, we can pass in card details, without PAN.
        Receiver_tokens kept in settings.py."""
        settings.logger.info('Start batch card process for Visa')
        card_log = []

        for card in card_info:
            put_account_status(1, card_id=card['id'])
            card_log.append(card['payment_token'])

        if len(card_log) > 0:
            settings.logger.info(str(card_log))

        url = '{}{}{}'.format(settings.SPREEDLY_BASE_URL, '/receivers/', self.receiver_token())
        settings.logger.info('Create request data {}'.format(card_info))
        request_data, file_name = self.request_body(card_info)
        settings.logger.info('POST URL {}, header: {}'.format(url, self.header))

        resp = self.post_request(url, self.header, request_data)
        self.response_handler(resp)

        return file_name

    def create_file_data(self, card_info):
        sequence_number = self.get_next_seq_number()

        detail_record_count = len(card_info)
        header = Header(
            source_id='LOYANG',
            destination_id='VISA',
            file_description='Bink user card registration information',
            file_create_date=self.format_datetime(arrow.now()),
            file_control_number=str(sequence_number).rjust(2, '0'),
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
        file.add_detail(
            Detail(
                promotion_type='VD',
                promotion_code='3GB16LOYANPVLOYANGSAUG16A',
                action_code='{{action_code}}',
                endpoint_code='LOYANG',
                promotion_group_id='LOYANG',
                cardholder_account_number='{{credit_card_number}}',
                external_cardholder_id='{{external_cardholder_id}}',
                effective_date='{{effective_date}}',
                termination_date='{{termination_date}}',
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

    def get_next_seq_number(self):
        # Visa have a sequence number limit of 99 per day.
        # Re-zero when the day changes
        with psycopg2.connect(settings.POSTGRES_URI) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT next_seq_number, sequence_date "
                            "FROM sequence_numbers "
                            "WHERE scheme_provider='visa' "
                            "AND type='ENROL';")

                seq_number, seq_date = cur.fetchone()

                if arrow.get(seq_date).date() != arrow.now().date():
                    seq_number = 0
                elif seq_number > 99:
                    raise ValueError('Visa file sequence number greater than 99. Cards not sent')

                cur.execute("UPDATE sequence_numbers "
                            "SET next_seq_number = %s, sequence_date=current_date "
                            "WHERE scheme_provider='visa' "
                            "AND type='ENROL';", (seq_number + 1,))

        return seq_number


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
