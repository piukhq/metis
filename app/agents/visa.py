import arrow
import settings
import json
import datetime
import time
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

    def request_body(self, payment_token):
        msgId = time.mktime(datetime.datetime.now().timetuple())  # 'Can this be a guid or similar?'
        partnerId = 'Visa to provide'
        distrChan = 'Visa to provide'

        data = {
            "msgId": msgId,
            "partnerId": partnerId,
            "cardNbr": "{{credit_card_number}}",
            "cmAlias1": payment_token,
            "distrChan": distrChan
        }

        body_data = '![CDATA[{' + json.dumps(data) + '}]]'
        return body_data

    def create_file_data(self, cards):
        detail_record_count = len(cards)
        header = Header(
            source_id='XXXX',
            destination_id='VISA',
            file_description='Enroll cards',
            file_create_date=self.format_datetime(arrow.now()),
            file_format_version='Merchant Registration',
            filler1='',
            filler2='',
            file_type_indicator='I',
            file_unique_text='',
            filler3=''
        )

        footer = Footer(
            record_count=str(detail_record_count).rjust(10, '0'),
            filler=''
        )

        file = VisaCardFile()
        file.set_header(header)
        file.set_footer(footer)

        for card in cards:
            file.add_detail(
                Detail(
                    promotion_type='XX',
                    promotion_code='XXXX',
                    action_code='A',
                    endpoint_code='XXXXXX',
                    promotion_group_id='XXXXXX',
                    cardholder_account_number='{{credit_card_number}}',
                    external_cardholder_id=card,
                    effective_date=self.format_datetime(arrow.now()),
                    termination_date='',
                    filler=''
                ),
            )

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


class Field(object):
    def __init__(self, **kwargs):
        if 'record_identifier' in kwargs:
            raise TypeError('you may not specify record_identifier in kwargs')
        for k, v in kwargs.items():
            setattr(self, k, v)


class Header(Field):
    fields = [
        ('record_type', 2),
        ('record_sub_type', 2),
        ('source_id', 6),
        ('destination_id', 6),
        ('file_description', 255),
        ('file_create_date', 8),
        ('file_format_version', 4),
        ('test_file_indicator', 1),
        ('filler1', 2),
        ('filler2', 25),
        ('file_type_indicator', 932),
        ('file_unique_text', 20),
        ('filler3', 650)
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
    fields = [
        ('record_type', 2),
        ('record_sub_type', 2),
        ('promotion_type', 2),
        ('promotion_code', 25),
        ('action_code', 1),
        ('endpoint_code', 6),
        ('promotion_group_id', 6),
        ('cardholder_account_number', 19),
        ('external_cardholder_id', 25),
        ('effective_date', 8),
        ('termination_date', 8),
        ('filler', 712),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.record_type = '10'
        self.record_sub_type = '01'


class Footer(Field):
    fields = [
        ('record_type', 2),
        ('record_sub_type', 2),
        ('record_count', 10),
        ('filler', 986),
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
        :param field_class: a class deriving from Field
        :param fields: an instance of field_class
        :return: the serialized string
        """
        data = []
        for field, length in field_class.fields:
            data.append(str(getattr(fields, field)).ljust(length))
        return '|'.join(data)

    def set_header(self, header):
        """
        set the header record for the file
        :param header: the header to use
        :return: None
        """
        self.header_string = self._serialize(Header, header)

    def set_footer(self, footer):
        """
        set the footer record for the file
        :param footer: the footer to use
        :return: None
        """
        self.footer_string = self._serialize(Footer, footer)

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
