from copy import deepcopy
from typing import Union, Type, TYPE_CHECKING

import requests

import settings
from app.agents.exceptions import OAuthError
from app.hermes import get_provider_status_mappings, put_account_status
from app.utils import resolve_agent
from vault import fetch_secrets

if TYPE_CHECKING:
    from app.agents.agent_base import AgentBase

# Username and password from Spreedly site - Loyalty Angels environments
PASSWORD = settings.Secrets.spreedly_oauth_password
USERNAME = settings.Secrets.spreedly_oauth_username

XML_HEADER = {"Content-Type": "application/xml"}


def get_spreedly_url(partner_slug: str) -> str:
    if partner_slug == "visa" and settings.VOP_SPREEDLY_BASE_URL and not settings.STUBBED_VOP_URL:
        return settings.VOP_SPREEDLY_BASE_URL
    return settings.SPREEDLY_BASE_URL


def refresh_oauth_password() -> None:
    global PASSWORD
    secret_name = "spreedly_oauth_password"
    secret_def = deepcopy(settings.Secrets.SECRETS_DEF[secret_name])
    if fetch_secrets(secret_name, secret_def) and PASSWORD != settings.Secrets.spreedly_oauth_password:
        PASSWORD = settings.Secrets.spreedly_oauth_password


def send_request(
    method: str,
    url: str,
    headers: dict,
    request_data: Union[dict, str] = None,
    log_response=True
) -> requests.Response:
    settings.logger.info(f"{method} Spreedly Request to URL: {url}")
    params = {
        "method": method,
        "url": url,
        "headers": headers
    }
    if request_data:
        params["data"] = request_data

    resp = requests.request(**params, auth=(USERNAME, PASSWORD))
    if resp.status_code in [401, 403]:
        settings.logger.info(f"Spreedly {method} status code: {resp.status_code}, reloading oauth password from Vault")
        refresh_oauth_password()
        resp = requests.request(**params, auth=(USERNAME, PASSWORD))

    if log_response:
        settings.logger.info(f"Spreedly {method} status code: {resp.status_code} response: {resp.text}")

    return resp


def create_receiver(hostname: str, receiver_type: str) -> requests.Response:
    """
    Creates a receiver on the Spreedly environment.
    This is a single call for each Payment card endpoint, Eg MasterCard, Visa and Amex = 3 receivers created.
    This generates a token which LA would store and use for sending credit card details, without the PAN, to
    the payment provider endsite. This creates the proxy service, Spreedly use this to attach the PAN.
    """
    url = f"{settings.SPREEDLY_BASE_URL}/receivers.xml"
    xml_data = f"<receiver><receiver_type>{receiver_type}</receiver_type><hostnames>{hostname}</hostnames></receiver>"
    return send_request("POST", url, XML_HEADER, xml_data, log_response=False)


def create_prod_receiver(receiver_type: str) -> requests.Response:
    """
    Creates a receiver on the Spreedly environment.
    This is a single call for each Payment card endpoint, Eg MasterCard, Visa and Amex = 3 receivers created.
    This generates a token which LA would store and use for sending credit card details, without the PAN, to
    the payment provider endsite. This creates the proxy service, Spreedly use this to attach the PAN.
    """
    url = f"{settings.SPREEDLY_BASE_URL}/receivers.xml"
    xml_data = f"<receiver><receiver_type>{receiver_type}</receiver_type></receiver>"
    return send_request("POST", url, XML_HEADER, xml_data, log_response=False)


def create_sftp_receiver(sftp_details: dict) -> requests.Response:
    """
    Creates a receiver on the Spreedly environment.
    This is a single call to create a receiver for an SFTP process.
    """
    url = f"{settings.SPREEDLY_BASE_URL}/receivers.xml"
    xml_data = (
        "<receiver>"
        "  <receiver_type>{receiver_type}</receiver_type>"
        "  <hostnames>{hostnames}</hostnames>"
        "  <protocol>"
        "    <user>{username}</user>"
        "    <password>{password}</password>"
        "  </protocol>"
        "</receiver>"
    ).format(**sftp_details)
    return send_request("POST", url, XML_HEADER, xml_data, log_response=False)


def add_card(card_info: dict) -> requests.Response:
    """
    Once the receiver has been created and token sent back, we can pass in card details, without PAN.
    Receiver_tokens kept in settings.py.
    """
    settings.logger.info(f"Start Add card for {card_info['partner_slug']}")

    agent_instance = get_agent(card_info["partner_slug"])
    header = agent_instance.header
    url = f"{get_spreedly_url(card_info['partner_slug'])}/receivers/{agent_instance.receiver_token()}"

    settings.logger.info(f"Create request data {card_info}")
    try:
        request_data = agent_instance.add_card_body(card_info)
    except OAuthError:
        # 5 = PROVIDER_SERVER_DOWN
        # TODO: get this from gaia
        put_account_status(5, card_id=card_info["id"])
        return None
    settings.logger.info(f"POST URL {url}, header: {header} *-* {request_data}")

    resp = send_request("POST", url, header, request_data)

    # get the status mapping for this provider from hermes.
    status_mapping = get_provider_status_mappings(card_info["partner_slug"])

    resp = agent_instance.response_handler(resp, "Add", status_mapping)

    # Set card_payment status in hermes using 'id' HERMES_URL
    if resp["status_code"] == 200:
        settings.logger.info("Card added successfully, calling Hermes to activate card.")
        # 1 = ACTIVE
        # TODO: get this from gaia
        card_status_code = 1
    else:
        settings.logger.info("Card add unsuccessful, calling Hermes to set card status.")
        card_status_code = resp.get("bink_status", 0)  # Defaults to pending

    hermes_data = {
        "card_id": card_info["id"]
    }

    if resp.get("response_state"):
        hermes_data["response_state"] = resp["response_state"]

    if resp.get("status_code"):
        hermes_data["response_status"] = resp["status_code"]

    if resp.get("message"):
        hermes_data["response_message"] = resp["message"]

    if card_info.get("retry_id"):
        hermes_data["retry_id"] = card_info["retry_id"]

    reply = put_account_status(card_status_code, **hermes_data)

    settings.logger.info(f'Sent add request to hermes status {reply.status_code}: data '
                         f'{" ".join([":".join([x, str(y)]) for x, y in hermes_data.items()])}')
    # Return response effect as in task but useful for test cases
    return resp


def remove_card(card_info: dict) -> requests.Response:
    settings.logger.info(f"Start Remove card for {card_info['partner_slug']}")

    agent_instance = get_agent(card_info["partner_slug"])
    header = agent_instance.header
    action_name = "Delete"

    if card_info["partner_slug"] == "visa":
        # Note the other agents call Spreedly to Unenrol. This is incorrect as Spreedly should not
        # be used as a Proxy to pass unmodified messages to the Agent. The use in add/enrol is an
        # example of correct because Spreedly inserts the PAN when forwarding our message to the Agent.
        # Note there is no longer any requirement to redact the card with with Spreedly so only VOP
        # needs to be called to unenrol a card.

        response_state, status_code, agent_status_code, agent_message, _ = \
            agent_instance.un_enroll(card_info, action_name)
        # Set card_payment status in hermes using 'id' HERMES_URL
        if status_code != 201:
            settings.logger.info("VOP Card delete unsuccessful, calling Hermes to log error/retry.")
            hermes_status_data = {
                "card_id": card_info["id"],
                "response_state": response_state,
                "response_status": agent_status_code,
                "response_message": agent_message,
                "response_action": "Delete"
            }
            if card_info.get("retry_id"):
                hermes_status_data["retry_id"] = card_info["retry_id"]
            put_account_status(None, **hermes_status_data)
        # put_account_status sends a async response back to Hermes.
        # The return values below are not functional as this runs in a celery task.
        # However, they have been kept for compatibility with other agents and to assist testing
        return {"response_status": response_state, "status_code": status_code}
    else:
        # Older call used with Agents prior to VOP which proxy through Spreedly
        # 'https://core.spreedly.com/v1/receivers/' + agent_instance.receiver_token()
        url = f"{settings.SPREEDLY_BASE_URL}/receivers/{agent_instance.receiver_token()}"

        try:
            request_data = agent_instance.remove_card_body(card_info)
        except OAuthError:
            # 5 = PROVIDER_SERVER_DOWN
            # TODO: get this from gaia
            put_account_status(5, card_id=card_info["id"])
            return None
        resp = send_request("POST", url, header, request_data)
        # get the status mapping for this provider from hermes.
        status_mapping = get_provider_status_mappings(card_info["partner_slug"])
        resp = agent_instance.response_handler(resp, action_name, status_mapping)
        # @todo View this when looking at Metis re-design
        # This response does nothing as it is in an celery task.  No message is returned to Hermes.
        # getting status mapping is wrong as it is not returned nor would it be used by Hermes.
        return resp


def reactivate_card(card_info: dict) -> requests.Response:
    settings.logger.info(f"Start reactivate card for {card_info['partner_slug']}")

    agent_instance = get_agent(card_info["partner_slug"])

    header = agent_instance.header
    url = f"{get_spreedly_url(card_info['partner_slug'])}/receivers/{agent_instance.receiver_token()}"
    request_data = agent_instance.reactivate_card_body(card_info)

    resp = send_request("POST", url, header, request_data)

    # get the status mapping for this provider from hermes.
    status_mapping = get_provider_status_mappings(card_info["partner_slug"])

    resp = agent_instance.response_handler(resp, "Reactivate", status_mapping)
    # Set card_payment status in hermes using 'id' HERMES_URL
    if resp["status_code"] == 200:
        settings.logger.info("Card added successfully, calling Hermes to activate card.")
        # 1 = ACTIVE
        # TODO: get this from gaia
        card_status_code = 1
    else:
        settings.logger.info("Card add unsuccessful, calling Hermes to set card status.")
        card_status_code = resp["bink_status"]
    put_account_status(card_status_code, card_id=card_info["id"])

    return resp


def get_agent(partner_slug: str) -> Type['AgentBase()']:
    agent_class = resolve_agent(partner_slug)
    return agent_class()


def retain_payment_method_token(payment_method_token: str, partner_slug: str = None) -> requests.Response:
    url = f"{get_spreedly_url(partner_slug)}/payment_methods/{payment_method_token}/retain.json"
    return send_request("PUT", url, {"Content-Type": "application/json"})
