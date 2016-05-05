from celery import Celery
client = None

celery = Celery("metis", broker='redis://localhost:6379/0')


@celery.task()
def add_together(a, b):
    return a + b
