from typing import TYPE_CHECKING

import requests

import settings
from app.action import ActionCode
from app.services import get_agent, get_spreedly_url, send_request

if TYPE_CHECKING:
    from app.agents.agent_base import AgentBase  # noqa


def basic_add_card(agent: str, card_info: dict) -> requests.Response:
    """
    Once the receiver has been created and token sent back, we can pass in card details, without PAN.
    Receiver_tokens kept in settings.py.
    """

    agent_instance = get_agent(agent)
    header = agent_instance.header
    url = f"{get_spreedly_url(agent)}/receivers/{agent_instance.receiver_token()}"
    settings.logger.info(f"Create request data {card_info}")
    request_data = agent_instance.add_card_body(card_info)
    settings.logger.info(f"POST URL {url}, header: {header} *-* {request_data}")
    req_resp = send_request("POST", url, header, request_data)
    resp = agent_instance.response_handler(req_resp, "Add", {})
    return resp


def basic_remove_card(agent: str, card_info: dict):
    settings.logger.info(f"Start Remove card for {agent}")
    card_info["action_code"] = ActionCode.DELETE
    agent_instance = get_agent(agent)
    header = agent_instance.header
    action_name = "Delete"

    if agent == "visa":
        return agent_instance.un_enroll(card_info, action_name)
    else:
        # Older call used with Agents prior to VOP which proxy through Spreedly
        # 'https://core.spreedly.com/v1/receivers/' + agent_instance.receiver_token()
        url = f"{settings.SPREEDLY_BASE_URL}/receivers/{agent_instance.receiver_token()}"

        request_data = agent_instance.remove_card_body(card_info)

        resp = send_request("POST", url, header, request_data)
        response_status = resp.status_code
        agent_message = resp.text

        return response_status, 200, "", agent_message, {}
