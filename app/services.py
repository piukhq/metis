import requests

from app.utils import resolve_agent
from app.hermes import provider_status_mapping
from settings import HERMES_URL, SERVICE_API_KEY, logger, SPREEDLY_RECEIVER_URL

# Username and password from Spreedly site - Loyalty Angels environments
password = '94iV3Iyvky86avhdjLgIh0z9IFeB0pw4cZvu64ufRgaur46mTM4xepsPDOdxVH51'
# Production
# This username is used for Amex testing, Visa and MasterCard use one above
username = '1Lf7DiKgkcx5Anw7QxWdDxaKtTa'
receiver_base_url = SPREEDLY_RECEIVER_URL
# Testing
# Username used for MasterCard and Visa testing only
# username = 'Yc7xn3gDP73PPOQLEB2BYpv31EV'


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
    logger.info('POST Spreedly Request to URL: {}'.format(url))
    resp = requests.post(url, auth=(username, password), headers=header, data=request_data)
    logger.info('Spreedly POST response: {}'.format(resp.text))
    return resp


def add_card(card_info):
    """Once the receiver has been created and token sent back, we can pass in card details, without PAN.
    Receiver_tokens kept in settings.py."""
    logger.info('Start Add card for {}'.format(card_info['partner_slug']))

    agent_instance = get_agent(card_info['partner_slug'])
    header = agent_instance.header
    url = '{}{}{}'.format(receiver_base_url, '/', agent_instance.receiver_token())

    logger.info('Create request data {}'.format(card_info))
    request_data = agent_instance.add_card_body(card_info)
    logger.info('POST URL {}, header: {} *-* {}'.format(url, header, request_data))

    resp = post_request(url, header, request_data)

    # get the status mapping for this provider from hermes.
    status_mapping = provider_status_mapping(card_info['partner_slug'])

    resp = agent_instance.response_handler(resp, 'Add', status_mapping)

    # Set card_payment status in hermes using 'id' HERMES_URL
    if resp["status_code"] == 200:
        logger.info('Metis calling Hermes set Status.')

        update_status_url = "{}/payment_cards/accounts/status/{}".format(HERMES_URL, card_info['id'])
        resp = requests.put(update_status_url,
                            headers={'content-type': 'application/json',
                                     'Authorization': 'Token {}'.format(SERVICE_API_KEY)},
                            json={"status": resp['bink_status']})

    return resp


def remove_card(card_info):
    logger.info('Start Remove card for {}'.format(card_info['partner_slug']))

    agent_instance = get_agent(card_info['partner_slug'])

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
