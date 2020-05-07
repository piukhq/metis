import pickle
from enum import Enum

import pika

import settings
from app.hermes import put_account_status
from app.tasks import add_card, remove_card, reactivate_card


class ActionCode(Enum):
    ADD = 'A'
    DELETE = 'D'
    REACTIVATE = 'R'
    ACTIVATE_MERCHANT = 'M'


def celery_handler(action_code, card_info):
    {ActionCode.ADD: lambda: add_card.delay(card_info),
     ActionCode.DELETE: lambda: remove_card.delay(card_info),
     ActionCode.REACTIVATE: lambda: reactivate_card.delay(card_info)}[action_code]()


def rabbitmq_handler(action_code, card_info):
    if settings.TESTING:
        # 1 = ACTIVE
        # TODO: get this from gaia
        card_status_code = 1
        put_account_status(card_status_code, card_id=card_info['id'])
        return

    credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASS)
    params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=5672, credentials=credentials)
    connection = pika.BlockingConnection(params)

    channel = connection.channel()
    queue_name = card_info['partner_slug']
    channel.queue_declare(queue_name, durable=True)
    channel.basic_publish(exchange='',
                          routing_key=queue_name,
                          body=pickle.dumps(card_info),
                          properties=pika.BasicProperties(delivery_mode=2))
    connection.close()


handlers = {
    'amex': celery_handler,
    'mastercard': celery_handler,
    # the current handler is 'visa': rabbitmq_handler, will become obsolete when this code is released
    'visa': celery_handler,
}


def process_card(action_code, card_info):
    card_info['action_code'] = action_code
    handlers[card_info['partner_slug']](action_code, card_info)
