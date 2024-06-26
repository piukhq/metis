import time
from typing import Any

import requests
from loguru import logger

from metis.settings import settings
from metis.utils import ctx


def _add_x_azure_ref_header(headers: dict) -> None:
    if ctx.x_azure_ref:
        headers |= {"x-azure-ref": ctx.x_azure_ref}


def get_provider_status_mappings(slug: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Authorization": f"Token {settings.SERVICE_API_KEY}"}
    _add_x_azure_ref_header(headers)
    status_mapping = requests.get(
        f"{settings.HERMES_URL}/payment_cards/provider_status_mappings/{slug}",
        headers=headers,
    ).json()
    return {x["provider_status_code"]: x["bink_status_code"] for x in status_mapping}


def put_account_status(
    status_code: int | None, card_id: int | None = None, token: str | None = None, **kwargs: Any
) -> requests.Response:
    resp = None
    if not (card_id or token):
        raise AttributeError("You must pass either a card_id or token to put_account_status.")

    # Un-enrol sends retry status and success/error status update but not payment card status
    request_data: dict[str, str | int | None] = {"status": status_code} if status_code is not None else {}

    if card_id:
        request_data["id"] = card_id
    else:
        request_data["token"] = token

    for kwarg in kwargs:
        request_data[kwarg] = kwargs[kwarg]

    count = 0
    max_count = 5

    headers = {"content-type": "application/json", "Authorization": f"Token {settings.SERVICE_API_KEY}"}
    _add_x_azure_ref_header(headers)

    while count < max_count:
        resp = requests.put(
            f"{settings.HERMES_URL}/payment_cards/accounts/status",
            headers=headers,
            json=request_data,
        )
        if resp.status_code < 400:
            break
        else:
            _handle_request_retry(count, max_count, card_id, token)
    if resp is None:
        raise ValueError("failed request PUT /payment_cards/accounts/status to Hermes")

    return resp


def _handle_request_retry(count: int, max_count: int, card_id: int | None, token: str | None) -> None:
    time.sleep(count)
    count += 1
    if count == 1:
        logger.info("Retry Payment Account Status Call Back for card/token: {}{}", card_id, token)
    elif count == max_count:
        logger.error(
            "Failed Payment Account Status Call Back: {}{}, given up after {} attempts", card_id, token, max_count
        )
