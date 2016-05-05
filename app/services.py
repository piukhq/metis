# Calls to Spreedly API.
import requests

# Username and password from Spreedly site - Loyalty Angels environments
username = 'Yc7xn3gDP73PPOQLEB2BYpv31EV'
password = 'aVodg3iJsJoLqsCvu3OQE36ztXZzR4V3Hk4VsBgOdReJVrtdg9NYOxWh5Nf4C3Lz'
header = {'Content-Type': 'application/xml'}


def create_receiver(hostname):
    """Creates a receiver on the Spreedly environment.
    This is a single call for each Payment card endpoint, Eg MasterCard, Visa and Amex = 3 receivers created.
    This generates a token which LA would store and use for sending credit card details, without the PAN, to
    the payment provider endsite. This creates the proxy service, Spreedly use this to attach the PAN."""
    url = 'https://core.spreedly.com/v1/receivers.xml'
    xml_data = '<receiver>' \
               '  <receiver_type>test</receiver_type>' \
               '  <hostnames>' + hostname + '</hostnames>' \
               '</receiver>'
    resp = requests.post(url, auth=(username, password), headers=header, data=xml_data)
    return resp


def end_site_receiver(hostname, receiver_token, payment_token):
    """Once the receiver has been created and token sent back, we can pass in card details, without PAN.
    Receiver_tokens kept in settings.py."""
    url = 'https://core.spreedly.com/v1/receivers/' + receiver_token + '/deliver.xml'
    xml_data = '<delivery>' \
               '  <payment_method_token>' + payment_token + '</payment_method_token>' \
               '  <url>' + hostname + '</url>' \
               '  <headers><![CDATA[Content-Type: application/json]]></headers>' \
               '  <body><![CDATA[{' \
               '    "card_number":"{{ credit_card_number }}" ' \
               '    }]]></body>' \
               '</delivery>'
    resp = requests.post(url, auth=(username, password), headers=header, data=xml_data)
    return resp
