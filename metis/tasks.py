from metis import services
from metis.celery import celery


@celery.task
def add_card(card_info):
    services.add_card(card_info)


@celery.task
def remove_card(card_info):
    services.remove_card(card_info)


@celery.task
def reactivate_card(card_info):
    services.reactivate_card(card_info)
