import os
import time
from datetime import datetime
from typing import TYPE_CHECKING

import requests
from loguru import logger
from requests.exceptions import ConnectionError, Timeout

from metis import settings
from metis.agents.exceptions import OAuthError
from metis.agents.visa_offers import VOPResultStatus
from metis.hermes import get_provider_status_mappings, put_account_status
from metis.prometheus.metrics import (
    STATUS_FAILED,
    STATUS_SUCCESS,
    mastercard_reactivate_counter,
    mastercard_reactivate_response_time_histogram,
    payment_card_enrolment_counter,
    payment_card_enrolment_reponse_time_histogram,
    push_metrics,
    unenrolment_counter,
    unenrolment_response_time_histogram,
)
from metis.utils import resolve_agent
from metis.vault import fetch_and_set_secret, get_azure_client

if TYPE_CHECKING:
    from metis.agents.agent_base import AgentBase

pid = os.getpid()
XML_HEADER = {"Content-Type": "application/xml"}


def push_mastercard_reactivate_metrics(response, card_info, request_time_taken):
    if card_info["partner_slug"] != "mastercard":
        return

    mastercard_reactivate_response_time_histogram.labels(status=response["status_code"]).observe(
        request_time_taken.total_seconds()
    )

    if response["status_code"] == 200:
        mastercard_reactivate_counter.labels(status=STATUS_SUCCESS).inc()
    else:
        mastercard_reactivate_counter.labels(status=STATUS_FAILED).inc()

    push_metrics(pid)


def push_unenrol_metrics_non_vop(response, card_info, request_time_taken):
    unenrolment_response_time_histogram.labels(
        provider=card_info["partner_slug"], status=response["status_code"]
    ).observe(request_time_taken.total_seconds())

    if response["status_code"] == 200:
        unenrolment_counter.labels(provider=card_info["partner_slug"], status=STATUS_SUCCESS).inc()
    else:
        unenrolment_counter.labels(provider=card_info["partner_slug"], status=STATUS_FAILED).inc()

    push_metrics(pid)


def get_spreedly_url(partner_slug: str) -> str:
    if partner_slug == "visa" and settings.VOP_SPREEDLY_BASE_URL and not settings.STUBBED_VOP_URL:
        return settings.VOP_SPREEDLY_BASE_URL
    return settings.SPREEDLY_BASE_URL


def refresh_oauth_credentials() -> None:
    if settings.AZURE_VAULT_URL:
        secret_defs = ["spreedly_oauth_password", "spreedly_oauth_username"]

        client = get_azure_client()

        for secret_name in secret_defs:
            try:
                secret_def = settings.Secrets.SECRETS_DEF[secret_name]
                fetch_and_set_secret(client, secret_name, secret_def)
                logger.info(f"{secret_name} refreshed from Vault.")
            except Exception as e:
                logger.error(f"Failed to get {secret_name} from Vault. Exception: {e}")

    else:
        logger.error(
            "Vault retry attempt due to Oauth error when AZURE_VAULT_URL not set. Have you set the"
            " SPREEDLY_BASE_URL to your local Pelops?"
        )


def send_request(  # noqa: PLR0913
    method: str,
    url: str,
    headers: dict,
    request_data: dict | str = None,
    log_response: bool = True,
    timeout: tuple = (5, 10),
) -> requests.Response:
    logger.info(f"{method} Spreedly Request to URL: {url}")
    params = {"method": method, "url": url, "headers": headers, "timeout": timeout}
    if request_data:
        params["data"] = request_data

    resp = send_retry_spreedly_request(
        **params, auth=(settings.Secrets.spreedly_oauth_username, settings.Secrets.spreedly_oauth_password)
    )
    if log_response:
        try:
            logger.info(f"Spreedly {method} status code: {resp.status_code}")
            logger.debug(f"Response content:\n{resp.text}")
        except AttributeError as e:
            logger.info(f"Spreedly {method} to URL: {url} failed response object error {e}")

    return resp


def send_retry_spreedly_request(**params):
    attempts = 0
    get_auth_attempts = 0
    resp = None
    while attempts < 4:
        attempts += 1
        try:
            resp = requests.request(**params)
        except (Timeout, ConnectionError) as e:
            retry = True
            resp = None
            logger.error(
                f"Spreedly {params['method']}, url:{params['url']}," f" Retriable exception {e} attempt {attempts}"
            )
        else:
            if resp.status_code in (401, 403):
                logger.info(
                    f"Spreedly {params['method']} status code: {resp.status_code}, "
                    f"reloading oauth password from Vault"
                )
                refresh_oauth_credentials()
                get_auth_attempts += 1
                if get_auth_attempts > 3:
                    time.sleep(2**get_auth_attempts - 2)
                if get_auth_attempts > 10:
                    break
                attempts = 0
                retry = True
            elif resp.status_code in (500, 501, 502, 503, 504, 492):
                logger.error(
                    f"Spreedly {params['method']}, url:{params['url']},"
                    f" status code: {resp.status_code}, Retriable error attempt {attempts}"
                )
                retry = True
            else:
                retry = False
        if retry:
            time.sleep(3**attempts - 1)  # 4 attempts at 2s, 8s, 26s, 63s or 0s if if oauth error

        else:
            break

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


def get_hermes_data(resp, card_id):
    hermes_data = {"card_id": card_id, "response_action": "Add"}

    if resp.get("response_state"):
        hermes_data["response_state"] = resp["response_state"]

    other_data = resp.get("other_data", {})
    if other_data.get("agent_card_uid"):
        hermes_data["agent_card_uid"] = other_data["agent_card_uid"]

    if resp.get("status_code"):
        hermes_data["response_status_code"] = resp["status_code"]

    if resp.get("agent_status_code"):
        hermes_data["response_status"] = resp["agent_status_code"]

    if resp.get("message"):
        hermes_data["response_message"] = resp["message"]

    return hermes_data


def add_card(card_info: dict) -> requests.Response:
    """
    Once the receiver has been created and token sent back, we can pass in card details, without PAN.
    Receiver_tokens kept in settings.py.
    """
    logger.info(f"Start Add card for {card_info['partner_slug']}")

    agent_instance = get_agent(card_info["partner_slug"])
    header = agent_instance.header
    url = f"{get_spreedly_url(card_info['partner_slug'])}/receivers/{agent_instance.receiver_token()}"

    logger.info(f"Create request data {card_info}")
    try:
        request_data = agent_instance.add_card_body(card_info)
    except OAuthError:
        # TODO: get this from gaia
        put_account_status(5, card_id=card_info["id"])
        return None
    logger.info(f"POST URL {url}, header: {header} *-* {request_data}")

    request_start_time = datetime.now()
    req_resp = send_request("POST", url, header, request_data)
    request_time_taken = datetime.now() - request_start_time

    # get the status mapping for this provider from hermes.
    status_mapping = get_provider_status_mappings(card_info["partner_slug"])

    try:
        resp = agent_instance.response_handler(req_resp, "Add", status_mapping)
    except AttributeError:
        resp = {"status_code": 504, "message": "Bad or no response from Spreedly"}

    # Set card_payment status in hermes using 'id' HERMES_URL
    if resp["status_code"] == 200:
        logger.info("Card added successfully, calling Hermes to activate card.")
        # TODO: get this from gaia
        card_status_code = 1
        payment_card_enrolment_counter.labels(
            provider=card_info["partner_slug"],
            status=STATUS_SUCCESS,
        ).inc()
    else:
        logger.info("Card add unsuccessful, calling Hermes to set card status.")
        card_status_code = resp.get("bink_status", 0)  # Defaults to pending
        payment_card_enrolment_counter.labels(
            provider=card_info["partner_slug"],
            status=STATUS_FAILED,
        ).inc()

    hermes_data = get_hermes_data(resp, card_info["id"])
    if resp["status_code"] == 422:  # Ensure that 422 responses get retried WAL-2992
        hermes_data["response_state"] = "Retry"

    if card_info.get("retry_id"):
        hermes_data["retry_id"] = card_info["retry_id"]

    reply = put_account_status(card_status_code, **hermes_data)

    logger.info(
        f"Sent add request to hermes status {reply.status_code}: data "
        f'{" ".join([":".join([x, str(y)]) for x, y in hermes_data.items()])}'
    )

    payment_card_enrolment_reponse_time_histogram.labels(
        provider=card_info["partner_slug"], status=resp["status_code"]
    ).observe(request_time_taken.total_seconds())

    push_metrics(pid)

    # Return response effect as in task but useful for test cases
    return resp


def hermes_unenroll_call_back(  # noqa: PLR0913
    card_info,
    action,
    deactivated_list,
    deactivate_errors,
    response_state,
    status_code,
    agent_status_code,
    agent_message,
    _,
):
    # Set card_payment status in hermes using 'id' HERMES_URL
    if status_code != 201:
        logger.info(
            f"Error in unenrol call back to Hermes VOP Card id: {card_info['id']} "
            f"{action} unsuccessful.  Response state {response_state}"
            f" {status_code}, {agent_status_code}, {agent_message}"
        )
    hermes_status_data = {
        "card_id": card_info["id"],
        "response_state": response_state,
        "response_status": agent_status_code,
        "response_message": agent_message,
        "response_action": action,
        "deactivated_list": deactivated_list,
        "deactivate_errors": deactivate_errors,
    }
    if card_info.get("retry_id"):
        hermes_status_data["retry_id"] = card_info["retry_id"]

    put_account_status(None, **hermes_status_data)

    return {response_state, status_code}


def remove_card(card_info: dict):
    logger.info(f"Start Remove card for {card_info['partner_slug']}")

    agent_instance = get_agent(card_info["partner_slug"])
    header = agent_instance.header
    action_name = "Delete"

    if card_info["partner_slug"] == "visa":
        # Note the other agents call Spreedly to Unenrol. This is incorrect as Spreedly should not
        # be used as a Proxy to pass unmodified messages to the Agent. The use in add/enrol is an
        # example of correct because Spreedly inserts the PAN when forwarding our message to the Agent.
        # Note there is no longer any requirement to redact the card with with Spreedly so only VOP
        # needs to be called to unenrol a card.

        # Currenly only VOP will need to deactivate first - it would do no harm on upgrading for all accounts to look to
        # see if there are activations but we will leave this until Metis has a common unenroll/delete code again

        # If there are activations in the list we must make sure they are deactivated first before unenrolling
        # It is probably better not to unenroll if any de-activations fail.  That way if a card with same PAN as a
        # deleted card is added it will not go active and pick up old activations (VOP retains this and re-links it!)
        # We will retry this call until all de-activations are done then unenrol.  We call back after each deactivation
        # so that if we retry only the remaining activations will be sent to this service

        activations = card_info.get("activations")
        deactivated_list = []
        deactivate_errors = {}
        if activations:
            all_deactivated = True
            for activation_index, deactivation_card_info in activations.items():
                logger.info(f"VOP Metis Unenrol Request - deactivating {activation_index}")
                deactivation_card_info["payment_token"] = card_info["payment_token"]
                deactivation_card_info["id"] = card_info["id"]
                response_status, status_code, agent_response_code, agent_message, _ = agent_instance.deactivate_card(
                    deactivation_card_info
                )
                if response_status == VOPResultStatus.SUCCESS.value:
                    deactivated_list.append(activation_index)
                else:
                    deactivate_errors[activation_index] = {
                        "response_status": response_status,
                        "agent_response_code": agent_response_code,
                        "agent_response_message": agent_message,
                    }
                    if response_status == VOPResultStatus.RETRY.value:
                        all_deactivated = False
                        # Only if you can retry the deactivation will we allow it to block the unenroll
                    elif response_status == VOPResultStatus.FAILED.value:
                        logger.error(
                            f"VOP Metis Unenrol Request for {card_info['id']}"
                            f"- permanent deactivation fail {activation_index}"
                        )
            if not all_deactivated:
                message = "Cannot unenrol some Activations still active and can be retried"
                logger.info(f"VOP Unenroll fail for {card_info['id']} {message}")

                status_code, response_state = hermes_unenroll_call_back(
                    card_info,
                    action_name,
                    deactivated_list,
                    deactivate_errors,
                    VOPResultStatus.RETRY.value,
                    "",
                    "",
                    message,
                    "",
                )
                return {"response_status": response_state, "status_code": status_code}

        # Do hermes call back of unenroll now that there are no outstanding activations
        response_state, status_code = hermes_unenroll_call_back(
            card_info,
            action_name,
            deactivated_list,
            deactivate_errors,
            *agent_instance.un_enroll(card_info, action_name, pid),
        )

        # put_account_status sends a async response back to Hermes.
        # The return values below are not functional as this runs in a celery task.
        # However, they have been kept for compatibility with other agents and to assist testing
        return {"response_status": response_state, "status_code": status_code}
    else:
        # Older call used with Agents prior to VOP which proxy through Spreedly
        url = f"{settings.SPREEDLY_BASE_URL}/receivers/{agent_instance.receiver_token()}"

        try:
            request_data = agent_instance.remove_card_body(card_info)
        except OAuthError:
            # TODO: get this from gaia
            put_account_status(5, card_id=card_info["id"])
            return None
        request_start_time = datetime.now()
        resp = send_request("POST", url, header, request_data)
        request_time_taken = datetime.now() - request_start_time

        # get the status mapping for this provider from hermes.
        status_mapping = get_provider_status_mappings(card_info["partner_slug"])
        resp = agent_instance.response_handler(resp, action_name, status_mapping)

        # Push unenrol metrics for amex and mastercard
        push_unenrol_metrics_non_vop(resp, card_info, request_time_taken)

        # @todo View this when looking at Metis re-design
        # This response does nothing as it is in an celery task.  No message is returned to Hermes.
        # getting status mapping is wrong as it is not returned nor would it be used by Hermes.

        return resp


def reactivate_card(card_info: dict) -> requests.Response:
    logger.info(f"Start reactivate card for {card_info['partner_slug']}")

    agent_instance = get_agent(card_info["partner_slug"])

    header = agent_instance.header
    url = f"{get_spreedly_url(card_info['partner_slug'])}/receivers/{agent_instance.receiver_token()}"
    request_data = agent_instance.reactivate_card_body(card_info)

    request_start_time = datetime.now()
    resp = send_request("POST", url, header, request_data)
    request_total_time = datetime.now() - request_start_time

    # get the status mapping for this provider from hermes.
    status_mapping = get_provider_status_mappings(card_info["partner_slug"])

    resp = agent_instance.response_handler(resp, "Reactivate", status_mapping)
    # Set card_payment status in hermes using 'id' HERMES_URL
    if resp["status_code"] == 200:
        logger.info("Card added successfully, calling Hermes to activate card.")
        # TODO: get this from gaia
        card_status_code = 1
    else:
        logger.info("Card add unsuccessful, calling Hermes to set card status.")
        card_status_code = resp["bink_status"]
    put_account_status(card_status_code, card_id=card_info["id"])
    push_mastercard_reactivate_metrics(resp, card_info, request_total_time)

    return resp


def get_agent(partner_slug: str) -> type["AgentBase()"]:
    agent_class = resolve_agent(partner_slug)
    return agent_class()


def retain_payment_method_token(payment_method_token: str, partner_slug: str = None) -> requests.Response:
    url = f"{get_spreedly_url(partner_slug)}/payment_methods/{payment_method_token}/retain.json"
    return send_request("PUT", url, {"Content-Type": "application/json"})
