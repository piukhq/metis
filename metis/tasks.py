from metis import services
from metis.celery import celery_app
from metis.enums import RetryTypes
from metis.utils import ctx


@celery_app.task
def add_card(card_info: dict, x_azure_ref: str | None = None) -> None:
    ctx.x_azure_ref = x_azure_ref
    services.add_card(card_info)


@celery_app.task
def remove_card(card_info: dict, x_azure_ref: str | None = None) -> None:
    ctx.x_azure_ref = x_azure_ref
    services.remove_card(card_info)


@celery_app.task
def reactivate_card(card_info: dict, x_azure_ref: str | None = None) -> None:
    ctx.x_azure_ref = x_azure_ref
    services.reactivate_card(card_info)


@celery_app.task
def remove_and_redact(card_info: dict, redact_only: bool, x_azure_ref: str | None = None) -> None:
    ctx.x_azure_ref = x_azure_ref
    if not redact_only:
        services.remove_card(card_info, retry_type=RetryTypes.REMOVE_AND_REDACT)

    services.redact_card(card_info)
