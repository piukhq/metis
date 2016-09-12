import base64
import hashlib
import settings
import jinja2
import os
import io
from lxml import etree

testing_url = 'http://latestserver.com/post.php'
testing_receiver_token = 'XsXRs91pxREDW7TAFbUc1TgosxU'
testing_endpoint = 'https://ws.mastercard.com/mtf/MRS/DiagnosticService'
production_url = 'https://ws.mastercard.com/mtf/MRS/DiagnosticService'
production_receiver_token = 'XsXRs91pxREDW7TAFbUc1TgosxU'
production_endpoint = 'https://ws.mastercard.com/mtf/MRS/DiagnosticService'


class MasterCard:
    header = {'Content-Type': 'application/xml'}

    def add_url(self):
        if not settings.TESTING:
            service_url = production_url
        else:
            service_url = testing_url
        return service_url

    def remove_url(self):
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
        return receiver_token + '/deliver.xml'

    def request_header(self):
        header = '<![CDATA[Content-Type: text/xml;charset=utf-8]]>'
        # header = 'Content-Type: text/xml;charset=utf-8'
        return header

    def add_card_request_body(self, card_ids):
        # Add the card data method in once doEcho testing is complete.
        # card_data(card_ids)
        soap_xml = self.create_soap_template()
        body_data = '<![CDATA[' + soap_xml + ']]>'
        return body_data

    def remove_card_request_body(self, card_ids):
        # Add the card data method in once doEcho testing is complete.
        # card_data(card_ids)
        soap_xml = self.create_soap_template()
        body_data = '<![CDATA[' + soap_xml + ']]>'
        return body_data

    # Use this method to set up the request data as json.
    def card_data(self, card_ids):
        # app_id = 'Get app id from MasterCard'
        # bank_product_code = 'MRS code for card product provided by MC'
        # program_identifier = 'MRS program id'
        data = {
            "app_id": 'Get app id from MasterCard',
            "bank_customer_number": card_ids[0],
            "member_ica": '17597',
            "bank_product_code": 'MRS code for card product provided by MC',
            "program_identifier": 'MRS program id'
        }

        return data

    def add_card_body(self, card_info):
        xml_data = '<delivery>' \
                   '  <payment_method_token>' + card_info[0]['payment_token'] + '</payment_method_token>' \
                   '  <url>' + self.add_url() + '</url>' \
                   '  <headers>' + self.request_header() + '</headers>' \
                   '  <body>' + self.add_card_request_body(card_info) + '</body>' \
                   '</delivery>'
        return xml_data

    def remove_card_body(self, card_info):
        xml_data = '<delivery>' \
                   '  <payment_method_token>' + card_info[0]['payment_token'] + '</payment_method_token>' \
                   '  <url>' + self.add_url() + '</url>' \
                   '  <headers>' + self.request_header() + '</headers>' \
                   '  <body>' + self.remove_card_request_body(card_info) + '</body>' \
                   '</delivery>'
        return xml_data

    def create_soap_template(self):
        template_loader = jinja2.FileSystemLoader(searchpath=os.path.dirname(__file__))
        template_env = jinja2.Environment(loader=template_loader)

        template_file = 'mc_template.xml'
        template = template_env.get_template(template_file)

        template_vars = {"app_id": 0,
                         "institution_name": "loyaltyangels",
                         "binary_security_token": "{{#binary_security_token}}{{/binary_security_token}}",
                         "utc_timestamp1": "{{#utc_timestamp}}{{/utc_timestamp}}",
                         "utc_timestamp2": "{{#utc_timestamp}}{{/utc_timestamp}}",
                         "body": 'Hello'
                         }
        output_text = template.render(template_vars)

        # Wrap the xml in {{#xmldsig}} tags for Spreedly to sign
        output_text = '{{#xmldsig}}' + output_text + '{{/xmldsig}}'
        return output_text

    def process_soap_xml(self, xml):
        xml_doc = etree.fromstring(xml.encode('utf-8'))
        tree = etree.ElementTree(xml_doc)

        bst_hash = self.digest_section(tree, 'BinarySecurityToken')
        xml = xml.replace('digest_1', bst_hash)

        time_stamp_hash = self.digest_section(tree, 'Timestamp')
        xml = xml.replace('digest_2', time_stamp_hash)

        identity_hash = self.digest_section(tree, 'identity')
        xml = xml.replace('digest_3', identity_hash)

        body_hash = self.digest_section(tree, 'Body')
        xml = xml.replace('digest_4', body_hash)

        # Now get the completed SignedInfo element and add it to the SignatureValue section
        xml_doc1 = etree.fromstring(xml.encode('utf-8'))
        tree1 = etree.ElementTree(xml_doc1)
        signed_info = self.get_xml_element(tree1, 'SignedInfo')
        signed_info = self.canonicalize_xml(signed_info)
        signed_info_str = signed_info.getvalue().decode("utf-8")  # etree.tostring(signed_info)
        signature_value = '{{#base64}}{{#rsa_sign}}sha512,' + signed_info_str + '{{/rsa_sign}}{{/base64}}'
        xml = xml.replace('signature_value', signature_value)
        # print(repr(xml))
        return xml

    def digest_section(self, tree, element_tag):
        elem = self.get_xml_element(tree, element_tag)
        # string_elem = etree.tostring(elem)
        can_b = self.canonicalize_xml(elem)
        c14n_body_node = can_b.getvalue().decode("utf-8")
        spreedly_digest_value = '{{#base64}}{{#digest}}sha256,'+c14n_body_node+'{{/digest}}{{/base64}}'
        return spreedly_digest_value

    def hashed_section(self, tree, element_tag):
        elem = self.get_xml_element(tree, element_tag)
        # string_elem = etree.tostring(elem)
        can_b = self.canonicalize_xml(elem)
        section_xml = can_b.getvalue()   # .decode("utf-8")
        return self.get_hash(section_xml)

    def get_xml_element(self, tree, element_tag):
        for element in tree.iter():
            if element_tag in element.tag:
                elem = etree.ElementTree(element)
                break
        return elem

    def get_hash(self, input_text):
        hash_object = hashlib.sha256(input_text)
        b_str = str(base64.b64encode(hash_object.digest()), 'utf-8')
        return b_str

    def canonicalize_xml(self, xml_part):
        canonicalized_xml = io.BytesIO()
        xml_part.write_c14n(canonicalized_xml, exclusive=True)
        return canonicalized_xml
