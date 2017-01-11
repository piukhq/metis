from app.tasks import add_card, remove_card
from enum import Enum
import settings
import pickle
import pika


class ActionCode(Enum):
    ADD = 'A'
    DELETE = 'D'


def celery_handler(action_code, card_info):
    {ActionCode.ADD: lambda: add_card.delay(card_info),
     ActionCode.DELETE: lambda: remove_card.delay(card_info)}[action_code]()


def rabbitmq_handler(action_code, card_info):
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
    'visa': rabbitmq_handler,
}


def process_card(action_code, card_info):
    card_info['action_code'] = action_code
    handlers[card_info['partner_slug']](action_code, card_info)
