#!/usr/bin/env python3
from app.agents.visa import Visa
from raven import Client
import settings
import pickle
import pika

if settings.SENTRY_DSN:
    sentry = Client(settings.SENTRY_DSN)


if __name__ == '__main__':
    credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASS)
    params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=5672, credentials=credentials)
    connection = pika.BlockingConnection(params)

    channel = connection.channel()
    queue_name = 'visa'

    out_of_messages = False

    for i in range(0, settings.FILES_PER_DAY):
        if out_of_messages:
            break

        card_infos = []

        for j in range(0, settings.CARDS_PER_FILE):
            state = channel.queue_declare(queue_name, durable=True, passive=True)

            if state.method.message_count == 0:
                out_of_messages = True
                break

            method, properties, body = channel.basic_get(queue_name, no_ack=True)
            card_infos.append(pickle.loads(body))

        agent = Visa()
        agent.create_cards(card_infos)

    connection.close()
