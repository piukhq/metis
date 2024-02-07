from metis import services
from metis.celery import celery_app
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
