from metis import services
from metis.celery import celery
from metis.utils import ctx


@celery.task
def add_card(card_info, x_azure_ref: str | None = None):
    ctx.x_azure_ref = x_azure_ref
    services.add_card(card_info)


@celery.task
def remove_card(card_info, x_azure_ref: str | None = None):
    ctx.x_azure_ref = x_azure_ref
    services.remove_card(card_info)


@celery.task
def reactivate_card(card_info, x_azure_ref: str | None = None):
    ctx.x_azure_ref = x_azure_ref
    services.reactivate_card(card_info)
