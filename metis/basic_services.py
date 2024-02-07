import os
from typing import TYPE_CHECKING, Literal, cast

from loguru import logger

from metis.action import ActionCode
from metis.agents.amex import Amex
from metis.agents.mastercard import MasterCard
from metis.agents.visa_offers import Visa
from metis.services import async_send_request, get_agent, get_spreedly_url
from metis.settings import settings

pid = os.getpid()


async def basic_add_card(agent: Literal["amex", "mastercard", "visa"], card_info: dict) -> dict:
    """
    Once the receiver has been created and token sent back, we can pass in card details, without PAN.
    Receiver_tokens kept in settings.py.
    """

    agent_instance = get_agent(agent)
    header = agent_instance.header
    url = f"{get_spreedly_url(agent)}/receivers/{agent_instance.receiver_token()}"
    logger.info("Create request data {}", card_info)
    request_data = agent_instance.add_card_body(card_info)
    logger.info("POST URL {}, header: {} *-* {}", url, header, request_data)
    req_resp = await async_send_request("POST", url, header, request_data)
    resp = agent_instance.response_handler(req_resp, "Add", card_info.get("status_map", {"BINK_UNKNOWN": "unknown"}))
    return resp


async def basic_remove_card(
    agent: Literal["amex", "mastercard", "visa"], card_info: dict
) -> tuple[str, int, str, str, dict]:
    logger.info("Start Remove card for {}", agent)
    card_info["action_code"] = ActionCode.DELETE
    agent_instance = get_agent(agent)
    header = agent_instance.header
    action_name = "Delete"

    if agent == "visa":
        if TYPE_CHECKING:
            agent_instance = cast(Visa, agent_instance)
        return await agent_instance.async_un_enroll(card_info, action_name, pid)
    else:
        if TYPE_CHECKING:
            agent_instance = cast(MasterCard | Amex, agent_instance)
        # Older call used with Agents prior to VOP which proxy through Spreedly
        url = f"{settings.SPREEDLY_BASE_URL}/receivers/{agent_instance.receiver_token()}"

        request_data = agent_instance.remove_card_body(card_info=card_info)

        req_resp = await async_send_request("POST", url, header, request_data)
        resp = agent_instance.response_handler(
            response=req_resp,
            action_name=action_name,
            status_mapping=card_info.get("status_map", {"BINK_UNKNOWN": "unknown"}),
        )

        return "n/a", resp["status_code"], "", resp["message"], {"bink_status": resp["bink_status"]}


async def mastercard_reactivate_card(card_info: dict) -> dict:
    logger.info("Start reactivate card for mastercard")
    mastercard_agent = MasterCard()
    header = mastercard_agent.header
    url = f"{get_spreedly_url('mastercard')}/receivers/{mastercard_agent.receiver_token()}"
    request_data = mastercard_agent.reactivate_card_body(card_info)
    req_resp = await async_send_request("POST", url, header, request_data)
    resp = mastercard_agent.response_handler(
        req_resp,
        "Reactivate",
        cast(dict[str, str], card_info.get("status_map", {"BINK_UNKNOWN": "unknown"})),
    )
    return resp
