#!/usr/bin/env python3
from collections import defaultdict
import pickle
import time
import os

from raven import Client
import pika

from app.agents.visa import Visa
from app.card_router import ActionCode
from app.slack import payment_card_notify
import settings

if settings.SENTRY_DSN:
    sentry = Client(settings.SENTRY_DSN)


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def reduce_card_data(card_info):
    totals = defaultdict(int)
    for ci in card_info:
        payment_token = ci['payment_token']
        action = ci['action_code']
        delta = 1 if action is ActionCode.ADD else -1
        totals[payment_token] += delta

    def find_card(token):
        return next(c for c in card_info if c['payment_token'] == token)

    new_card_info = []
    for payment_token, total in totals.items():
        if total == 0:
            continue

        if total < 0:
            action = ActionCode.DELETE
        else:
            action = ActionCode.ADD

        card = find_card(payment_token)
        card['action_code'] = action
        new_card_info.append(card)
    return new_card_info


if __name__ == '__main__':
    credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASS)
    params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=5672, credentials=credentials)
    connection = pika.BlockingConnection(params)

    channel = connection.channel()
    queue_name = 'visa'

    card_infos = []
    for i in range(0, settings.FILES_PER_DAY * settings.CARDS_PER_FILE):
        state = channel.queue_declare(queue_name, durable=True, passive=True)

        if state.method.message_count == 0:
            break

        method, properties, body = channel.basic_get(queue_name, no_ack=True)
        card_infos.append(pickle.loads(body))

    card_infos = reduce_card_data(card_infos)

    processed_files = []
    for chunk_index, chunk in enumerate(chunks(card_infos, settings.CARDS_PER_FILE)):
        print('processing card group #{}'.format(chunk_index + 1))
        agent = Visa()
        print('sending cards to spreedly...')
        file_name = agent.create_cards(chunk)
        file_path = os.path.join('/home/spreedlyftp/', file_name)

        processed_files.append(file_name)

        print('giving spreedly a moment to catch up...')
        time.sleep(settings.SPREEDLY_SEND_DELAY)

    connection.close()

    payment_card_notify(
        'Visa card enrolments have been sent to Spreedly. Relevant files: [{}]'.format(
            ', '.join('`{}`'.format(x) for x in processed_files)))
