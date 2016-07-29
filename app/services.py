# Calls to Spreedly API.
import requests
from app.utils import resolve_agent

# Username and password from Spreedly site - Loyalty Angels environments
password = '94iV3Iyvky86avhdjLgIh0z9IFeB0pw4cZvu64ufRgaur46mTM4xepsPDOdxVH51'
# Testing
# username = 'Yc7xn3gDP73PPOQLEB2BYpv31EV'
# Production
username = '1Lf7DiKgkcx5Anw7QxWdDxaKtTa'
header = {'Content-Type': 'application/xml'}


def create_receiver(hostname, receiver_type):
    """Creates a receiver on the Spreedly environment.
    This is a single call for each Payment card endpoint, Eg MasterCard, Visa and Amex = 3 receivers created.
    This generates a token which LA would store and use for sending credit card details, without the PAN, to
    the payment provider endsite. This creates the proxy service, Spreedly use this to attach the PAN."""
    url = 'https://core.spreedly.com/v1/receivers.xml'
    xml_data = '<receiver>' \
               '  <receiver_type>' + receiver_type + '</receiver_type>' \
               '  <hostnames>' + hostname + '</hostnames>' \
               '</receiver>'
    resp = requests.post(url, auth=(username, password), headers=header, data=xml_data)
    return resp


def create_prod_receiver(receiver_type):
    """Creates a receiver on the Spreedly environment.
    This is a single call for each Payment card endpoint, Eg MasterCard, Visa and Amex = 3 receivers created.
    This generates a token which LA would store and use for sending credit card details, without the PAN, to
    the payment provider endsite. This creates the proxy service, Spreedly use this to attach the PAN."""
    url = 'https://core.spreedly.com/v1/receivers.xml'
    xml_data = '<receiver>' \
               '  <receiver_type>' + receiver_type + '</receiver_type>' \
               '</receiver>'
    resp = requests.post(url, auth=(username, password), headers=header, data=xml_data)
    return resp


def create_sftp_receiver(sftp_details):
    """Creates a receiver on the Spreedly environment.
    This is a single call to create a receiver for an SFTP process.
    """
    url = 'https://core.spreedly.com/v1/receivers.xml'
    xml_data = '<receiver>' \
               '  <receiver_type>' + sftp_details["receiver_type"] + '</receiver_type>' \
               '  <hostnames>' + sftp_details["hostnames"] + '</hostnames>' \
               '  <protocol>' \
               '    <user>' + sftp_details["username"] + '</user>' \
               '    <password>' + sftp_details["password"] + '</password>' \
               '  </protocol>' \
               '</receiver>'
    resp = requests.post(url, auth=(username, password), headers=header, data=xml_data)
    return resp


def end_site_receiver(partner_slug, payment_token):
    """Once the receiver has been created and token sent back, we can pass in card details, without PAN.
    Receiver_tokens kept in settings.py."""
    agent_class = get_agent_class(partner_slug)
    agent_instance = agent_class()

    url = 'https://core.spreedly.com/v1/receivers/' + agent_instance.receiver_token() + '/deliver.xml'
    xml_data = '<delivery>' \
               '  <payment_method_token>' + payment_token + '</payment_method_token>' \
               '  <url>' + agent_instance.url() + '</url>' \
               '  <headers>' + agent_instance.request_header() + '</headers>' \
               '  <body>' + agent_instance.request_body(payment_token) + '</body>' \
               '</delivery>'
    resp = requests.post(url, auth=(username, password), headers=header, data=xml_data)
    return resp


def get_agent_class(partner_slug):
    try:
        return resolve_agent(partner_slug)
    except KeyError:
        raise(404, 'No such agent')
