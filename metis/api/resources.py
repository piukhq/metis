from time import perf_counter
from typing import TYPE_CHECKING, Annotated, Literal, cast

from fastapi import APIRouter, Body, Depends, Header, Response, status
from loguru import logger
from pydantic import ValidationError

from metis.action import ActionCode
from metis.agents.exceptions import OAuthError
from metis.agents.visa_offers import Visa
from metis.api.deps import async_azure_ref_dep, handle_payment_card_schema_validation_error, sync_azure_ref_dep
from metis.api.deps import authorized as auth_dep
from metis.api.schemas import (
    CardInfoRedactSchema,
    CardInfoSchema,
    CreateReceiverSchema,
    FoundationAddSchema,
    FoundationDeleteSchema,
    FoundationResponseSchema,
    FoundationRetainSchema,
    VisaActivationResponseSchema,
    VisaDeactivationResponseSchema,
    VisaVOPActivationSchema,
    VisaVOPDeactivationSchema,
)
from metis.basic_services import basic_add_card, basic_remove_card, mastercard_reactivate_card
from metis.celery import celery_app
from metis.prometheus.metrics import (
    STATUS_FAILED,
    STATUS_SUCCESS,
    spreedly_retain_processing_seconds_histogram,
    status_counter,
)
from metis.services import create_prod_receiver, retain_payment_method_token
from metis.tasks import add_card, reactivate_card, remove_and_redact, remove_card
from metis.utils import ctx

if TYPE_CHECKING:
    from pydantic import BaseModel


healthz_router = APIRouter()
auth_router = APIRouter(
    dependencies=[
        Depends(async_azure_ref_dep),
        Depends(sync_azure_ref_dep),
        Depends(auth_dep),
    ],
)
openapi_payment_card_responses: dict[int | str, dict] = {
    status.HTTP_200_OK: {
        "description": "Successful Response",
        "content": {
            "application/json": {
                "schema": {
                    "type": "string",
                    "example": "Success",
                }
            }
        },
    },
    status.HTTP_400_BAD_REQUEST: {
        "description": "Validation Error",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "example": {"detail": "Request parameters not complete"},
                },
            }
        },
    },
}


class XMLResponse(Response):
    media_type = "application/xml"


def get_routing_key(priority: int) -> str:
    # as reported on https://docs.celeryq.dev/projects/kombu/en/latest/reference/kombu.html#queue for Kombu v5.3.4
    # max_priority(int)  # noqa: ERA001
    # For example if the value is 10,
    # then messages can delivered to this queue can have a priority value between 0 and 10,
    # where 10 is the highest priority.
    return "metis.tasks.high" if priority > 5 else "metis.tasks.low"


def process_card(action_code: str, card_info: dict, *, priority: int, x_azure_ref: str | None = None) -> None:
    card_info["action_code"] = action_code

    match action_code:
        case ActionCode.ADD:
            task = add_card
        case ActionCode.DELETE:
            task = remove_card
        case ActionCode.REACTIVATE:
            task = reactivate_card

    task.apply_async(
        args=[card_info],
        kwargs={"x_azure_ref": x_azure_ref},
        exchange="metis-celery-tasks",
        routing_key=get_routing_key(priority),
        priority=priority,
    )


@healthz_router.get("/healthz", tags=["healthz"])
def healthz() -> dict:
    return {}


@healthz_router.get("/livez", tags=["healthz"])
def livez() -> dict:
    return {}


@healthz_router.get(
    "/readyz",
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Error",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "example": {"celery": "failed to connect to celery broker due to error: {ERROR}"},
                    },
                }
            },
        },
    },
    tags=["healthz"],
)
def readyz(response: Response) -> dict:
    try:
        celery_app.control.inspect().ping()
    except Exception as ex:
        logger.exception("failed to connect to celery broker")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"celery": f"failed to connect to celery broker due to error: {ex!r}"}

    return {}


# FIXME: This endpoint is only ever used to set up a new spreedly environment
# It is not used in normal journeys and so should probably live in a different
# module
@auth_router.post(
    "/payment_service/create_receiver",
    response_class=XMLResponse,
    responses={
        status.HTTP_200_OK: {
            "description": "Response content and status code vary based on spreedly response",
            "content": {
                "application/xml": {
                    "schema": {
                        "type": "string",
                    },
                }
            },
        },
    },
    tags=["payment_account"],
)
async def create_receiver(req_data: CreateReceiverSchema) -> Response:
    resp = await create_prod_receiver(req_data.receiver_type)
    return XMLResponse(resp.text, status_code=resp.status_code)


async def payment_card_action(action_code: ActionCode, req_data: dict[str, str], priority: int) -> tuple[str, int]:
    action_name = {ActionCode.ADD: "add", ActionCode.DELETE: "delete"}[action_code]
    logger.info("Received {} payment card request: {}", action_name, req_data)
    if action_code == ActionCode.ADD:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        resp_text = " No reply received"
        try:
            response_start_time = perf_counter()
            resp = await retain_payment_method_token(req_data["payment_token"], req_data.get("partner_slug"))
            response_total_time = perf_counter() - response_start_time
            status_code = resp.status_code
            reason = resp.reason_phrase
            resp_text = resp.text

            spreedly_retain_processing_seconds_histogram.labels(
                provider=req_data.get("partner_slug"), status=status_code
            ).observe(response_total_time)
        except AttributeError:
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
            reason = "Connection failed after retry"
        except Exception as e:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            reason = f"Exception {e!r}"

        if status_code != status.HTTP_200_OK:
            status_counter.labels(provider=req_data.get("partner_slug"), status=STATUS_FAILED).inc()
            logger.info(
                f"Retain unsuccessful: HTTP {status_code} {reason} {resp_text}"
                f'Payment token: {req_data.get("payment_token")} partner: {req_data.get("partner_slug")}'
            )
            return "Retain unsuccessful", status.HTTP_400_BAD_REQUEST

        status_counter.labels(provider=req_data.get("partner_slug"), status=STATUS_SUCCESS).inc()

    process_card(action_code, req_data, priority=priority, x_azure_ref=ctx.x_azure_ref)

    return "Success", status.HTTP_200_OK


@auth_router.post(
    "/payment_service/payment_card",
    description="Endpoint used by Hermes, will spawn a celery task",
    dependencies=[Depends(handle_payment_card_schema_validation_error)],
    responses=openapi_payment_card_responses,
    tags=["payment_account"],
)
async def payment_card_add(
    response: Response,
    card_info: CardInfoSchema,
    x_priority: Annotated[int, Header(ge=0, le=10)] = 10,
) -> str:
    resp_body, status_code = await payment_card_action(
        ActionCode.ADD, card_info.model_dump(exclude_none=True), priority=x_priority
    )
    response.status_code = status_code
    return resp_body


@auth_router.delete(
    "/payment_service/payment_card",
    description="Endpoint used by Hermes, will spawn a celery task",
    dependencies=[Depends(handle_payment_card_schema_validation_error)],
    responses=openapi_payment_card_responses,
    tags=["payment_account"],
)
async def payment_card_delete(
    response: Response,
    card_info: CardInfoSchema,
    x_priority: Annotated[int, Header(ge=0, le=10)] = 10,
) -> str:
    resp_body, status_code = await payment_card_action(
        ActionCode.DELETE, card_info.model_dump(exclude_none=True), priority=x_priority
    )
    response.status_code = status_code
    return resp_body


@auth_router.post(
    "/payment_service/payment_card/update",
    description="Endpoint used by Hermes, will spawn a celery task",
    dependencies=[
        Depends(handle_payment_card_schema_validation_error),
    ],
    status_code=200,
    responses=openapi_payment_card_responses,
    tags=["payment_account"],
)
def update_payment_card(card_info: CardInfoSchema, x_priority: Annotated[int, Header(ge=0, le=10)] = 10) -> str:
    req_data = card_info.model_dump(exclude_none=True)
    logger.info("Received reactivate payment card request: {}", req_data)
    process_card(ActionCode.REACTIVATE, req_data, priority=x_priority, x_azure_ref=ctx.x_azure_ref)
    return "Success"


@auth_router.post(
    "/payment_service/payment_card/unenrol_and_redact",
    description="Endpoint used by Hermes, will spawn a celery task",
    dependencies=[Depends(handle_payment_card_schema_validation_error)],
    responses=openapi_payment_card_responses,
    status_code=status.HTTP_200_OK,
    tags=["payment_account"],
)
async def payment_card_delete_and_redact(
    card_info: CardInfoRedactSchema, x_priority: Annotated[int, Header(ge=0, le=10)] = 10
) -> str:
    req_data = card_info.model_dump(exclude_none=True)
    req_data["action_code"] = ActionCode.DELETE
    redact_only = req_data.pop("redact_only", False)
    logger.info("Received delete_and_redact request for card: {} redact_only: {}", req_data["id"], redact_only)

    remove_and_redact.apply_async(
        args=[req_data],
        kwargs={"x_azure_ref": ctx.x_azure_ref, "redact_only": redact_only},
        exchange="metis-celery-tasks",
        routing_key=get_routing_key(x_priority),
        priority=x_priority,
    )

    return "Success"


@auth_router.post(
    "/visa/activate/",
    description="Endpoint used by Hermes",
    response_model=VisaActivationResponseSchema,
    tags=["visa"],
)
async def visa_activate(response: Response, payload: VisaVOPActivationSchema) -> dict:
    visa = Visa()
    response_status, status_code, agent_response_code, agent_message, other_data = await visa.activate_card(
        payload.model_dump()
    )
    response.status_code = status_code
    return {
        "response_status": response_status,
        "agent_response_code": agent_response_code,
        "agent_response_message": agent_message,
        "activation_id": other_data.get("activation_id", ""),
    }


@auth_router.post(
    "/visa/deactivate/",
    description="Endpoint used by Hermes",
    response_model=VisaDeactivationResponseSchema,
    tags=["visa"],
)
async def visa_deactivate(response: Response, payload: VisaVOPDeactivationSchema) -> dict:
    visa = Visa()
    response_status, status_code, agent_response_code, agent_message, _ = await visa.async_deactivate_card(
        payload.model_dump()
    )
    response.status_code = status_code
    return {
        "response_status": response_status,
        "agent_response_code": agent_response_code,
        "agent_response_message": agent_message,
    }


"""
    Foundation interface is intended to be used by data correction scripts in the first instance
    It does basic actions without any background processing and returns a json dict
    Note it does not map the called service response code to http return codes; 200 if api call is success even if
    the called service returns an error.  The response data has a status_code field which should be checked
"""


def set_ret() -> dict[str, str | int]:
    return {
        "status_code": 0,
        "resp_text": "",
        "reason": "",
        "bink_status": "",
        "agent_response_code": "",
        "agent_retry_status": "",
    }


def map_response(resp: dict, ret: dict) -> None:
    ret["status_code"] = resp["status_code"]
    ret["bink_status"] = resp.get("bink_status")
    ret["resp_text"] = resp.get("response_state")
    ret["reason"] = resp["message"]
    ret["agent_response_code"] = resp.get("agent_status_code")
    ret["agent_retry_status"] = resp.get("response_state")


class InvalidParams(Exception):
    pass


def foundation_check_request(schema: type["BaseModel"], agent: str, req_data: dict, ret: dict) -> None:
    try:
        req_data = schema(**req_data).model_dump(exclude_none=True)
    except ValidationError as e:
        ret["reason"] = f"Invalid/Missing Request Parameters: {e!r}"
        ret["agent_retry_status"] = "Failed"
        raise InvalidParams from None
    if agent not in ("visa", "mastercard", "amex"):
        ret["reason"] = "Invalid Agent"
        ret["agent_retry_status"] = "Failed"
        raise InvalidParams


@auth_router.post(
    "/foundation/spreedly/{agent}/retain",
    status_code=status.HTTP_200_OK,
    response_model=FoundationResponseSchema,
    tags=["foundation"],
)
async def foundation_spreedly_retrain(
    agent: str,
    req_data: Annotated[
        dict,
        Body(
            example={
                "id": 0,
                "payment_token": "string",
            }
        ),
    ],
) -> dict[str, str | int]:
    ret = set_ret()
    try:
        foundation_check_request(FoundationRetainSchema, agent, req_data, ret)
        resp = await retain_payment_method_token(req_data["payment_token"], agent)
        ret["status_code"] = resp.status_code
        ret["resp_text"] = resp.text
        ret["reason"] = resp.reason_phrase
    except AttributeError:
        ret["status_code"] = status.HTTP_504_GATEWAY_TIMEOUT
        ret["reason"] = "Connection failed after retry"
        ret["agent_retry_status"] = "Failed"
    except InvalidParams:
        pass
    except Exception as e:
        ret["status_code"] = status.HTTP_500_INTERNAL_SERVER_ERROR
        ret["reason"] = f"Exception {e}"
        ret["agent_retry_status"] = "Failed"

    return ret


@auth_router.post(
    "/foundation/spreedly/{agent}/add",
    status_code=status.HTTP_200_OK,
    response_model=FoundationResponseSchema,
    tags=["foundation"],
)
async def foundation_spreedly_add(
    # cannot set the type of agent here as fastapi will raise a validation error if the value does not match
    agent: str,
    req_data: Annotated[
        dict,
        Body(
            example={
                "card_token": "string",
                "status_map": {},
            }
        ),
    ],
) -> dict[str, str | int]:
    ret = set_ret()
    try:
        foundation_check_request(FoundationAddSchema, agent, req_data, ret)
        resp_dict = await basic_add_card(cast(Literal["amex", "mastercard", "visa"], agent), req_data)
        map_response(resp_dict, ret)

    except OAuthError:
        ret["reason"] = "OAuthError"
        ret["agent_retry_status"] = "Failed"
    except InvalidParams:
        pass
    except Exception as e:
        ret["status_code"] = status.HTTP_500_INTERNAL_SERVER_ERROR
        ret["reason"] = f"Exception {e}"
        ret["agent_retry_status"] = "Failed"

    return ret


@auth_router.post(
    "/foundation/{agent}/remove",
    status_code=status.HTTP_200_OK,
    response_model=FoundationResponseSchema,
    tags=["foundation"],
)
async def foundation_remove(
    # cannot set the type of agent here as fastapi will raise a validation error if the value does not match
    agent: str,
    req_data: Annotated[
        dict,
        Body(
            example={
                "partner_slug": "string",
                "status_map": {},
            }
        ),
    ],
) -> dict[str, str | int]:
    ret = set_ret()
    try:
        foundation_check_request(FoundationDeleteSchema, agent, req_data, ret)
        response_status, api_code, agent_error_code, agent_message, other = await basic_remove_card(
            cast(Literal["amex", "mastercard", "visa"], agent), req_data
        )
        ret["status_code"] = api_code
        ret["resp_text"] = ""
        ret["reason"] = agent_message
        ret["bink_status"] = other.get("bink_status", "unknown")
        ret["agent_response_code"] = agent_error_code
        ret["agent_retry_status"] = response_status
    except OAuthError:
        ret["reason"] = "OAuthError"
        ret["agent_retry_status"] = "Failed"
    except InvalidParams:
        pass
    except Exception as e:
        ret["status_code"] = 500
        ret["reason"] = f"Exception {e}"
        ret["agent_retry_status"] = "Failed"

    return ret


@auth_router.post(
    "/foundation/spreedly/mastercard/reactivate",
    status_code=status.HTTP_200_OK,
    response_model=FoundationResponseSchema,
    tags=["foundation"],
)
async def foundation_mastercard_reactivate(
    req_data: Annotated[
        dict,
        Body(
            example={
                "card_token": "string",
                "status_map": {},
            }
        ),
    ],
) -> dict[str, str | int]:
    ret = set_ret()
    try:
        foundation_check_request(FoundationAddSchema, "mastercard", req_data, ret)
        # response_status, status_code, agent_response_code, agent_message, _
        resp = await mastercard_reactivate_card(req_data)
        map_response(resp, ret)

    except OAuthError:
        ret["reason"] = "OAuthError"
        ret["agent_retry_status"] = "Failed"
    except InvalidParams:
        pass
    except Exception as e:
        ret["status_code"] = status.HTTP_500_INTERNAL_SERVER_ERROR
        ret["reason"] = f"Exception {e}"
        ret["agent_retry_status"] = "Failed"

    return ret
