import time

import requests
from loguru import logger

from metis import settings


def get_provider_status_mappings(slug):
    status_mapping = requests.get(
        f"{settings.HERMES_URL}/payment_cards/provider_status_mappings/{slug}",
        headers={"Content-Type": "application/json", "Authorization": f"Token {settings.SERVICE_API_KEY}"},
    ).json()
    return {x["provider_status_code"]: x["bink_status_code"] for x in status_mapping}


def put_account_status(status_code, card_id=None, token=None, **kwargs):
    resp = None
    if not (card_id or token):
        raise AttributeError("You must pass either a card_id or token to put_account_status.")

    # Un-enrol sends retry status and success/error status update but not payment card status
    request_data = {"status": status_code} if status_code is not None else {}

    if card_id:
        request_data["id"] = card_id
    else:
        request_data["token"] = token

    for kwarg in kwargs:
        request_data[kwarg] = kwargs[kwarg]

    count = 0
    max_count = 5
    while count < max_count:
        resp = requests.put(
            f"{settings.HERMES_URL}/payment_cards/accounts/status",
            headers={"content-type": "application/json", "Authorization": f"Token {settings.SERVICE_API_KEY}"},
            json=request_data,
        )
        if resp.status_code < 400:
            break
        else:
            time.sleep(count)
            count += 1
            if count == 1:
                logger.info(f"Retry Payment Account Status Call Back for card/token: {card_id}{token}")
            elif count == max_count:
                logger.error(
                    f"Failed Payment Account Status Call Back: {card_id}{token}, "
                    f"given up after {max_count} attempts"
                )

    return resp