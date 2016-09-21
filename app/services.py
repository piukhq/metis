import requests
from app.utils import resolve_agent
from settings import HERMES_URL, SERVICE_API_KEY

# Username and password from Spreedly site - Loyalty Angels environments
password = '94iV3Iyvky86avhdjLgIh0z9IFeB0pw4cZvu64ufRgaur46mTM4xepsPDOdxVH51'
# Testing
# Username used for MasterCard and Visa testing only
# username = 'Yc7xn3gDP73PPOQLEB2BYpv31EV'
# Production
# This username is used for Amex testing, Visa and MasterCard use one above
username = '1Lf7DiKgkcx5Anw7QxWdDxaKtTa'
receiver_base_url = 'https://core.spreedly.com/v1/receivers'


def create_receiver(hostname, receiver_type):
    header = {'Content-Type': 'application/xml'}
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
    header = {'Content-Type': 'application/xml'}
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
    header = {'Content-Type': 'application/xml'}
    url = '{}{}'.format(receiver_base_url, '.xml')  # 'https://core.spreedly.com/v1/receivers.xml'
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


def post_request(url, header, request_data):
    resp = requests.post(url, auth=(username, password), headers=header, data=request_data)
    return resp


def add_card(card_info):
    """Once the receiver has been created and token sent back, we can pass in card details, without PAN.
    Receiver_tokens kept in settings.py."""
    agent_instance = get_agent(card_info[0]['partner_slug'])
    header = agent_instance.header
    url = '{}{}{}'.format(receiver_base_url, '/', agent_instance.receiver_token())
    # url = 'https://core.spreedly.com/v1/receivers/' + agent_instance.receiver_token()
    request_data = agent_instance.add_card_body(card_info)

    resp = post_request(url, header, request_data)
    resp = agent_instance.response_handler(resp, 'Add')

    # Set card_payment status in hermes using 'id' HERMES_URL
    if resp["status_code"] == 200:
        update_status_url = "{}/payment_cards/accounts/status/{}".format(HERMES_URL, card_info[0]['id'])
        token = 'Token {}'.format(SERVICE_API_KEY)
        data = {"status": 1}
        resp = requests.put(update_status_url,
                            headers={'content-type': 'application/json', 'Authorization': token},
                            json=data)

    return resp


def remove_card(card_info):
    agent_instance = get_agent(card_info[0]['partner_slug'])

    header = agent_instance.header
    url = '{}{}{}'.format(receiver_base_url, '/', agent_instance.receiver_token())
    # url = 'https://core.spreedly.com/v1/receivers/' + agent_instance.receiver_token()
    request_data = agent_instance.remove_card_body(card_info)

    resp = post_request(url, header, request_data)
    resp = agent_instance.response_handler(resp, 'Delete')
    return resp


def get_agent(partner_slug):
    try:
        agent_class = resolve_agent(partner_slug)
        return agent_class()
    except KeyError:
        raise(404, 'No such agent')
    except Exception as ex:
        raise(404, ex)
