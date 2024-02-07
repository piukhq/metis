from celery import Celery
from kombu import Exchange, Queue

from metis.settings import settings

exchange = Exchange("metis-celery-tasks", type="topic", durable=True)


celery_app = Celery(
    "metis-tasks",
    broker=settings.CELERY_BROKER_URL,
)
celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    accept_content=["pickle", "json", "msgpack", "yaml"],
    worker_enable_remote_control=False,
    timezone="Europe/London",
    enable_utc=True,
    task_default_exchange="metis-celery-tasks",
    task_default_routing_key="metis.tasks.high",
    task_queues={
        Queue(
            "metis:high",
            exchange=exchange,
            durable=True,
            delivery_mode="persistent",
            auto_delete=False,
            routing_key="metis.tasks.high",
            max_priority=10,
        ),
        Queue(
            "metis:low",
            exchange=exchange,
            durable=True,
            delivery_mode="persistent",
            auto_delete=False,
            routing_key="metis.tasks.low",
            max_priority=10,
        ),
    },
)
celery_app.autodiscover_tasks(["metis"])
