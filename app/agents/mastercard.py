import settings
import jinja2
import os
from lxml import etree


if settings.TESTING:
    # MASTERCARD_URL = 'https://ws.mastercard.com/mtf/MRS/DiagnosticService'
    MASTERCARD_URL = 'http://latestserver.com/post.php'
    MASTERCARD_RECEIVER_TOKEN = 'XsXRs91pxREDW7TAFbUc1TgosxU'
else:
    MASTERCARD_URL = 'https://ws.mastercard.com/MRS/CustomerService'
    MASTERCARD_RECEIVER_TOKEN = 'SiXfsuR5TQJ87wjH2O5Mo1I5WR'
MASTERCARD_DO_ECHO_URL = 'https://ws.mastercard.com/MRS/DiagnosticService'


class MasterCard:
    header = {'Content-Type': 'application/xml'}

    def add_url(self):
        return MASTERCARD_URL

    def remove_url(self):
        return MASTERCARD_URL

    def receiver_token(self):
        return MASTERCARD_RECEIVER_TOKEN + '/deliver.xml'

    def request_header(self):
        header = '<![CDATA[Content-Type: text/xml;charset=utf-8]]>'
        return header

    def response_handler(self, response, action, status_mapping):
        if response.status_code >= 300:
            try:
                resp_content = response.json()
                psp_message = resp_content['errors'][0]['message']
            except ValueError:
                psp_message = 'Could not access the PSP receiver'

            message = 'Problem connecting to PSP. Action: MasterCard {}. Error:{}'.format(action, psp_message)
            settings.logger.error(message)
            return {'message': message, 'status_code': response.status_code}

        try:
            xml_doc = etree.fromstring(response.text)
            string_elem = xml_doc.xpath("//body")[0].text
            xml_start_point = xml_doc.xpath("//body")[0].text.find('<?xml')
            soap_xml = string_elem[xml_start_point:]
            xml_soap_doc = etree.fromstring(soap_xml.encode('utf-8'))
            payment_method_token = xml_doc.xpath("//payment_method/token")
            mastercard_fault = xml_soap_doc.xpath("//faultstring")
            mastercard_fault_code = xml_soap_doc.xpath("//ns2:code",
                                                       namespaces={'ns2': 'http://common.ws.mcrewards.mastercard.com/'})
        except Exception as e:
            message = str('MasterCard {} problem processing response.'.format(action))
            resp = {'message': message, 'status_code': 422}
            settings.logger.error(message, exc_info=1)

        if mastercard_fault:
            # Not a good response, log the MasterCard error message and code, respond with 422 status
            message = "MasterCard {} unsuccessful - Token: {}, {}, {} {}".format(action,
                                                                                 payment_method_token[0].text,
                                                                                 mastercard_fault[0].text,
                                                                                 "Code:",
                                                                                 mastercard_fault_code[0].text)
            settings.logger.info(message)
            resp = {'message': action + 'MasterCard Fault recorded. Code: ' + mastercard_fault_code[0].text,
                    'status_code': 422}
        else:
            # could be a good response
            message = "MasterCard {} successful - Token: {}, {}".format(action,
                                                                        payment_method_token[0].text,
                                                                        "MasterCard successfully processed")
            settings.logger.info(message)
            resp = {'message': message, 'status_code': response.status_code}

        if mastercard_fault_code and mastercard_fault_code in status_mapping:
            resp['bink_status'] = status_mapping[mastercard_fault_code]
        else:
            resp['bink_status'] = status_mapping['BINK_UNKNOWN']
        return resp

    def add_card_body(self, card_info):
        xml_data = '<delivery>' \
                   '  <payment_method_token>' + card_info['payment_token'] + '</payment_method_token>' \
                   '  <url>' + self.add_url() + '</url>' \
                   '  <headers>' + self.request_header() + '</headers>' \
                   '  <body>' + self.add_card_request_body(card_info) + '</body>' \
                   '</delivery>'
        return xml_data

    def add_card_request_body(self, card_id):
        # Add the card data method in once doEcho testing is complete.
        # card_data(card_ids)
        soap_xml = self.add_card_soap_template(card_id)
        body_data = '<![CDATA[' + soap_xml + ']]>'
        return body_data

    def add_card_soap_template(self, card_id):
        template_env = self.jinja_environment()
        template_file = 'mc_enroll_template.xml'
        template = template_env.get_template(template_file)

        template_vars = {"app_id": '',
                         "institution_name": "loyaltyangels",
                         "binary_security_token": "{{#binary_security_token}}{{/binary_security_token}}",
                         "utc_timestamp1": "{{#utc_timestamp}}{{/utc_timestamp}}",
                         "utc_timestamp2": "{{#utc_timestamp}}{{/utc_timestamp}}",
                         "bank_customer_number": card_id['payment_token'],
                         "member_ica": '17597',
                         "bank_account_number": '{{credit_card_number}}',
                         "account_status_code": '1',
                         "bank_product_code": 'MCCLA',
                         "program_identifier": 'LAVN'
                         }
        output_text = template.render(template_vars)

        # Wrap the xml in {{#xmldsig}} tags for Spreedly to sign
        output_text = '{{#xml_dsig}}' + output_text + '{{/xml_dsig}}'
        return output_text

    def remove_card_body(self, card_id):
        xml_data = '<delivery>' \
                   '  <payment_method_token>' + card_id['payment_token'] + '</payment_method_token>' \
                   '  <url>' + self.remove_url() + '</url>' \
                   '  <headers>' + self.request_header() + '</headers>' \
                   '  <body>' + self.remove_card_request_body() + '</body>' \
                   '</delivery>'
        return xml_data

    def remove_card_request_body(self):
        soap_xml = self.remove_card_soap_template()
        body_data = '<![CDATA[' + soap_xml + ']]>'
        return body_data

    def remove_card_soap_template(self):
        template_env = self.jinja_environment()
        template_file = 'mc_remove_template.xml'
        template = template_env.get_template(template_file)

        template_vars = {"app_id": "{{credit_card_number}}",
                         "institution_name": "loyaltyangels",
                         "binary_security_token": "{{#binary_security_token}}{{/binary_security_token}}",
                         "utc_timestamp1": "{{#utc_timestamp}}{{/utc_timestamp}}",
                         "utc_timestamp2": "{{#utc_timestamp}}{{/utc_timestamp}}"
                         }
        output_text = template.render(template_vars)

        # Wrap the xml in {{#xmldsig}} tags for Spreedly to sign
        output_text = '{{#xml_dsig}}' + output_text + '{{/xml_dsig}}'
        return output_text

    def do_echo_body(self, card_info):
        # DoEcho url MTF
        do_echo_url = MASTERCARD_DO_ECHO_URL
        xml_data = '<delivery>' \
                   '  <payment_method_token>' + card_info['payment_token'] + '</payment_method_token>' \
                   '  <url>' + do_echo_url + '</url>' \
                   '  <headers>' + self.request_header() + '</headers>' \
                   '  <body>' + self.do_echo_request_body() + '</body>' \
                   '</delivery>'
        return xml_data

    def do_echo_request_body(self):
        # MasterCards doEcho test request.
        soap_xml = self.do_echo_soap_template()
        body_data = '<![CDATA[' + soap_xml + ']]>'
        return body_data

    def do_echo_soap_template(self):
        template_env = self.jinja_environment()
        template_file = 'mc_do_echo_template.xml'
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
        output_text = '{{#xml_dsig}}' + output_text + '{{/xml_dsig}}'
        return output_text

    def jinja_environment(self):
        template_path = os.path.join(os.path.dirname(__file__), "templates")
        template_loader = jinja2.FileSystemLoader(searchpath=template_path)
        template_env = jinja2.Environment(loader=template_loader)
        return template_env

    def get_xml_element(self, tree, element_tag):
        for element in tree.iter():
            if element_tag in element.tag:
                elem = etree.ElementTree(element)
                return elem
