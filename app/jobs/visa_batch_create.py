#!/usr/bin/env python3
from collections import defaultdict
import pickle
import time
import os
import pika

from app.agents.visa import Visa
from app.action import ActionCode
from app.teams import payment_card_notify
import settings


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def reduce_card_data(card_info):
    totals = defaultdict(int)
    for (ci, delivery_tag) in card_info:
        payment_token = ci['payment_token']
        action = ci['action_code']
        delta = 1 if action is ActionCode.ADD else -1
        totals[payment_token] += delta

    def find_card(token):
        return next(c for c in card_info if c[0]['payment_token'] == token)

    new_card_info = []
    dropped = []
    for payment_token, total in totals.items():
        if total == 0:
            dropped.append(find_card(payment_token))
            continue

        if total < 0:
            action = ActionCode.DELETE
        else:
            action = ActionCode.ADD

        card = find_card(payment_token)
        card[0]['action_code'] = action
        new_card_info.append(card)
    return new_card_info, dropped


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

        method, properties, body = channel.basic_get(queue_name)
        card_infos.append((pickle.loads(body), method.delivery_tag))

    card_infos, dropped = reduce_card_data(card_infos)

    print('acking dropped cards')
    for _, delivery_tag in dropped:
        channel.basic_ack(delivery_tag)

    processed_files = []
    for chunk_index, chunk in enumerate(chunks(card_infos, settings.CARDS_PER_FILE)):
        delivery_tags = [c[1] for c in chunk]
        chunk = [c[0] for c in chunk]
        print('processing card group #{}'.format(chunk_index + 1))
        agent = Visa()
        print('sending cards to spreedly...')
        file_name = agent.create_cards(chunk)

        print('acking messages in card group...')
        for delivery_tag in delivery_tags:
            channel.basic_ack(delivery_tag)

        file_path = os.path.join('/home/spreedlyftp/', file_name)

        processed_files.append(file_name)

        print('giving spreedly a moment to catch up...')
        time.sleep(settings.SPREEDLY_SEND_DELAY)

    connection.close()

    payment_card_notify(
        'Visa card enrolments have been sent to Spreedly. Relevant files: [{}]'.format(
            ', '.join('`{}`'.format(x) for x in processed_files)))
