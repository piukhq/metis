import arrow
import base64
import hashlib
import settings
import jinja2
import os
import io
from lxml import etree

testing_url = 'http://latestserver.com/post.php'
testing_receiver_token = 'YFteSZZ8lbjnxgHb1OR5tbR2oG7'
testing_endpoint = 'https://ws.mastercard.com/mtf/MRS/CustomerService'
production_url = ''
production_receiver_token = ''
production_endpoint = 'https://ws.mastercard.com/MRS/CustomerService'


class MasterCard:
    def url(self):
        if not settings.TESTING:
            service_url = production_url
        else:
            service_url = testing_url
        return service_url

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

    def request_body(self, card_ids):
        # app_id = 'Get app id from MasterCard'
        bank_customer_number = card_ids[0]
        # member_ica = '17597'  # confirmed in Letitia email of 11/05/2016
        # bank_product_code = 'MRS code for card product provided by MC'
        # program_identifier = 'MRS program id'

        soap_xml = self.create_soap_template()

        body_data = '![CDATA[{' + soap_xml + '}]]'
        return body_data

    def create_soap_template(self):
        template_loader = jinja2.FileSystemLoader(searchpath=os.path.dirname(__file__))
        template_env = jinja2.Environment(loader=template_loader)

        template_file = 'mc_template.xml'
        template = template_env.get_template(template_file)

        template_vars = {"app_id": 0,
                         "institution_name": "LoyaltyAngels",
                         "digest_1": 'digest_1',
                         "digest_2": 'digest_2',
                         "digest_3": 'digest_3',
                         "digest_4": 'digest_4',
                         "signature_value": 'signature_value',
                         "time_created": self.format_datetime(arrow.utcnow()),
                         "time_expires": self.format_datetime(arrow.utcnow().replace(hours=4)),
                         "body": 'Hello',
                         }
        output_text = template.render(template_vars)

        return output_text

    def process_soap_xml(self, xml):
        xml_doc = etree.fromstring(xml.encode('ascii'))
        tree = etree.ElementTree(xml_doc)

        bst_hash = self.hashed_section(tree, 'BinarySecurityToken')
        xml = xml.replace('digest_1', bst_hash)

        time_stamp_hash = self.hashed_section(tree, 'Timestamp')
        xml = xml.replace('digest_2', time_stamp_hash)

        identity_hash = self.hashed_section(tree, 'identity')
        xml = xml.replace('digest_3', identity_hash)

        body_hash = self.hashed_section(tree, 'Body')
        xml = xml.replace('digest_4', body_hash)

        # Now get the completed SignedInfo element and add it to th SignatureValue section
        xml_doc1 = etree.fromstring(xml.encode('ascii'))
        tree1 = etree.ElementTree(xml_doc1)
        signed_info = self.get_xml_element(tree1, 'SignedInfo')
        xml = xml.replace('signature_value', etree.tostring(signed_info).decode("utf-8"))
        # print(repr(xml))
        return xml

    def hashed_section(self, tree, element_tag):
        elem = self.get_xml_element(tree, element_tag)

        can_b = self.canonicalize_xml(elem)
        section_xml = can_b.getvalue().decode("utf-8")
        return self.get_hash(section_xml)

    def get_xml_element(self, tree, element_tag):
        for element in tree.iter():
            if element_tag in element.tag:
                elem = etree.ElementTree(element)
                break
        return elem

    def get_hash(self, input_text):
        hash_object = hashlib.sha256(input_text.encode('utf-8'))
        b_str = str(base64.b64encode(hash_object.digest()), 'utf-8')
        return b_str

    def canonicalize_xml(self, xml_part):
        canonicalized_xml = io.BytesIO()
        xml_part.write_c14n(canonicalized_xml)
        return canonicalized_xml

    @staticmethod
    def format_datetime(date_time):
        """
        formats an <arrow> datetime into the format expected by Visa
        :param date_time: the <arrow> datetime to be formatted
        :return: a datetime string in the format 'YYYY-MM-DDTHH:mm:ssZZ'
        """
        date_time_str = date_time.format('YYYY-MM-DDTHH:mm:ssZZ')
        date_time_str = date_time_str.replace('-00:00', 'Z')
        return date_time_str
