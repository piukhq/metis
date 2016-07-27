import arrow
import hashlib
import hmac
import os
import settings
import xml.etree.ElementTree as et
from handylib.factory import create_factory


class Spreedly(object):

    provider = 'spreedly'

    def __init__(self, provider):
        assert self.provider == provider

    def save(self, xml):
        root = et.fromstring(xml)
        if signature_for(root, settings.SPREEDLY_SIGNING_SECRET, xml):
            date_now = arrow.now()
            list_logs = []
            saved = True
            file_path = os.path.join(settings.APP_DIR, 'logs', 'file_log.txt')
            for transaction in root.findall('transaction'):
                date = date_now
                succeeded = transaction.find('succeeded').text
                state = transaction.find('state').text
                token = transaction.find('token').text
                out_item = '{}, {}, {}, {} \n'.format(date, succeeded, state, token)
                list_logs.append(out_item)

            with open(file_path, 'a') as log_file:
                for item in list_logs:
                    log_file.write(item)

            return saved


def signature_for(root, secret, xml):

    for signed in root.findall('transaction/signed'):
        hash = {
            'MD5': hashlib.md5,
            'SHA1': hashlib.sha1,
            'SHA256': hashlib.sha256,
            'SHA512': hashlib.sha512,
        }

        signature = signed.find('signature').text
        algorithm = signed.find('algorithm').text
        fields = signed.find('fields').text.split(" ")
        values = []
        for field in fields:
            val = root.find('transaction/' + field)
            if val.text is not None:
                values.append(val.text)
            else:
                values.append('')

        signature_data = "|".join(values)
        signature_data_bytes = signature_data.encode('utf-8')
        secret_key = secret.encode('utf-8')
        hash_function = hash.get(algorithm.upper())
        result = hmac.new(secret_key, msg=signature_data_bytes, digestmod=hash_function).hexdigest()
        return hmac.compare_digest(result, signature)


def register():
    factory = create_factory('process_agents')
    factory.register('spreedly', Spreedly)
