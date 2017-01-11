import celery as c
import raven
from raven.contrib.celery import register_signal, register_logger_signal
import settings

sentry = raven.Client(settings.SENTRY_DSN)


class Celery(c.Celery):

    def on_configure(self):

        # register a custom filter to filter out duplicate logs
        register_logger_signal(sentry)

        # hook into the Celery error handler
        register_signal(sentry)


celery = Celery()
celery.config_from_object(settings)
