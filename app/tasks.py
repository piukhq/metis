from app.celery import celery
from app import services


@celery.task
def add_card(card_info):
    try:
        # result = add_card(card_info)
        # response_text = result.content
        # status_code = result.status_code
        services.add_card(card_info)
    except Exception as e:
        # response_text = str({'Error': 'Problem sending the payment card information. Message: {}'.format(e)})
        # status_code = 400
        raise e


@celery.task
def remove_card(card_info):
    try:
        # result = remove_card(card_info)
        # response_text = result.content
        # status_code = result.status_code
        services.remove_card(card_info)
    except Exception as e:
        # response_text = str({'Error': 'Problem removing the payment card. Message: {}'.format(e)})
        # status_code = 400
        raise e
