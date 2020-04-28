import requests

from app.utils import resolve_agent
from app.agents.exceptions import OAuthError
from app.hermes import get_provider_status_mappings, put_account_status
import settings

# Username and password from Spreedly site - Loyalty Angels environments
password = '4m8tVKWHvakjhfBXnRVDbfkOArB9NvAyo9U6lWtVulb2thuI6T439blRbQWGwQcH'
# Production
# This username is used for Amex testing, Visa and MasterCard use one above
username = '1Lf7DiKgkcx5Anw7QxWdDxaKtTa'
# Testing
# Username used for MasterCard and Visa testing only
# username = 'Yc7xn3gDP73PPOQLEB2BYpv31EV'


def create_receiver(hostname, receiver_type):
    header = {'Content-Type': 'application/xml'}
    """Creates a receiver on the Spreedly environment.
    This is a single call for each Payment card endpoint, Eg MasterCard, Visa and Amex = 3 receivers created.
    This generates a token which LA would store and use for sending credit card details, without the PAN, to
    the payment provider endsite. This creates the proxy service, Spreedly use this to attach the PAN."""
    url = settings.SPREEDLY_BASE_URL + '/receivers.xml'
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
    url = settings.SPREEDLY_BASE_URL + '/receivers.xml'
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
    url = settings.SPREEDLY_BASE_URL + '/receivers.xml'
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
    settings.logger.info('POST Spreedly Request to URL: {}'.format(url))
    resp = requests.post(url, auth=(username, password), headers=header, data=request_data)
    settings.logger.info('Spreedly POST response: {}'.format(resp.text))
    return resp


def put_request(url, header, request_data):
    settings.logger.info('PUT Spreedly Request to URL: {}'.format(url))
    resp = requests.put(url, auth=(username, password), headers=header, data=request_data)
    settings.logger.info('Spreedly PUT response: {}'.format(resp.text))
    return resp


def add_card(card_info):
    """Once the receiver has been created and token sent back, we can pass in card details, without PAN.
    Receiver_tokens kept in settings.py."""
    settings.logger.info('Start Add card for {}'.format(card_info['partner_slug']))

    agent_instance = get_agent(card_info['partner_slug'])
    header = agent_instance.header
    url = '{}/receivers/{}'.format(settings.SPREEDLY_BASE_URL, agent_instance.receiver_token())

    settings.logger.info('Create request data {}'.format(card_info))
    try:
        request_data = agent_instance.add_card_body(card_info)
    except OAuthError:
        # 5 = PROVIDER_SERVER_DOWN
        # TODO: get this from gaia
        put_account_status(5, card_id=card_info['id'])
        return None
    settings.logger.info('POST URL {}, header: {} *-* {}'.format(url, header, request_data))

    resp = post_request(url, header, request_data)

    # get the status mapping for this provider from hermes.
    status_mapping = get_provider_status_mappings(card_info['partner_slug'])

    resp = agent_instance.response_handler(resp, 'Add', status_mapping)

    # Set card_payment status in hermes using 'id' HERMES_URL
    if resp["status_code"] == 200:
        settings.logger.info('Card added successfully, calling Hermes to activate card.')
        # 1 = ACTIVE
        # TODO: get this from gaia
        card_status_code = 1
    else:
        settings.logger.info('Card add unsuccessful, calling Hermes to set card status.')
        card_status_code = resp['bink_status']
    put_account_status(card_status_code, card_id=card_info['id'])

    return resp


def remove_card(card_info):
    settings.logger.info('Start Remove card for {}'.format(card_info['partner_slug']))

    agent_instance = get_agent(card_info['partner_slug'])
    header = agent_instance.header

    if card_info['partner_slug'] == 'visa':
        # Note the other agents use Spreedly as a Proxy which may need to be changed at some stage by adding to each
        # agent_instance an un_enroll method and removing remove_card_body(card_info)
        # For VOP we will un-enroll directly with VOP and not use Spreedly as a Proxy, however, a new Spreedly call will
        # be made to redact the Payment method.
        # VOP Un-enroll
        success, resp = agent_instance.un_enroll(card_info)
        if not success:
            settings.logger.info(
                f"Un-enroll failed for card {card_info['partner_slug']} account id {card_info['id']}"
            )
        # if the unroll fails it does not need to be retied but we will continue to remove card from spreedly
        url = f'{settings.SPREEDLY_BASE_URL}/v1/payment_methods/{agent_instance.receiver_token}/redact.json'

        redacted = False
        try:
            redact_resp = put_request(url, header, "")
            if redact_resp.status_code < 300:
                redacted = True
        except OAuthError:
            pass
        if not redacted:
            settings.logger.info(
                f"Un-enroll Spreedly redact failed for card {card_info['partner_slug']} account id {card_info['id']}"
            )
    else:
        # Older call used with Agents prior to VOP which proxy through Spreedly
        # 'https://core.spreedly.com/v1/receivers/' + agent_instance.receiver_token()
        url = '{}/receivers/{}'.format(settings.SPREEDLY_BASE_URL, agent_instance.receiver_token())

        try:
            request_data = agent_instance.remove_card_body(card_info)
        except OAuthError:
            # 5 = PROVIDER_SERVER_DOWN
            # TODO: get this from gaia
            put_account_status(5, card_id=card_info['id'])
            return None
        resp = post_request(url, header, request_data)

    # get the status mapping for this provider from hermes.
    status_mapping = get_provider_status_mappings(card_info['partner_slug'])

    resp = agent_instance.response_handler(resp, 'Delete', status_mapping)
    return resp


def reactivate_card(card_info):
    settings.logger.info('Start reactivate card for {}'.format(card_info['partner_slug']))

    agent_instance = get_agent(card_info['partner_slug'])

    header = agent_instance.header
    url = '{}/receivers/{}'.format(settings.SPREEDLY_BASE_URL, agent_instance.receiver_token())
    request_data = agent_instance.reactivate_card_body(card_info)

    resp = post_request(url, header, request_data)

    # get the status mapping for this provider from hermes.
    status_mapping = get_provider_status_mappings(card_info['partner_slug'])

    resp = agent_instance.response_handler(resp, 'Reactivate', status_mapping)
    # Set card_payment status in hermes using 'id' HERMES_URL
    if resp["status_code"] == 200:
        settings.logger.info('Card added successfully, calling Hermes to activate card.')
        # 1 = ACTIVE
        # TODO: get this from gaia
        card_status_code = 1
    else:
        settings.logger.info('Card add unsuccessful, calling Hermes to set card status.')
        card_status_code = resp['bink_status']
    put_account_status(card_status_code, card_id=card_info['id'])

    return resp


def get_agent(partner_slug):
    agent_class = resolve_agent(partner_slug)
    return agent_class()


def retain_payment_method_token(payment_method_token):
    url = '{}/payment_methods/{}/retain.json'.format(settings.SPREEDLY_BASE_URL, payment_method_token)
    resp = requests.put(url, auth=(username, password), headers={'Content-Type': 'application/json'})
    return resp
