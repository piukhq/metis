from collections.abc import Generator

import jwt
from fastapi import Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from loguru import logger

from metis.settings import settings
from metis.utils import ctx

HTTP_HEADER_ENCODING = "iso-8859-1"


def parse_token(auth_header: str) -> dict | bool | None:
    """
    Verifies that an access-token is valid and meant for this app.
    """
    auth = auth_header.encode(HTTP_HEADER_ENCODING).split()
    if not auth or auth[0].lower() != b"token":
        return None

    token = auth[1].decode()

    if token == settings.SERVICE_API_KEY:
        return True

    token_contents = jwt.decode(token, settings.TOKEN_SECRET, algorithms=["HS256"])

    return token_contents


def authorized(authorization: str = Header(None)) -> None:
    if not authorization:
        # Unauthorized
        raise HTTPException(401)

    try:
        parse_token(authorization)
    except jwt.DecodeError:
        raise HTTPException(401, "Token is invalid") from None

    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token has expired") from None


# async and sync functions set different contexts so we need x_azure_ref in both
async def async_azure_ref_dep(x_azure_ref: str = Header(None)) -> None:
    ctx.x_azure_ref = x_azure_ref


def sync_azure_ref_dep(x_azure_ref: str = Header(None)) -> None:
    ctx.x_azure_ref = x_azure_ref


def handle_payment_card_schema_validation_error(request: Request) -> Generator[None, None, None]:
    try:
        yield
    except RequestValidationError as exc:
        action = {"POST": "add", "DELETE": "delete"}[request.method]
        logger.error(
            "Received {} payment card request failed - reason: {} - request body: {}",
            action,
            exc,
            exc.body,
        )
        raise HTTPException(
            detail="Request parameters not complete",
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from None
