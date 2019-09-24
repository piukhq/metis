import logging

from ddtrace import tracer
from ddtrace.contrib.flask import TraceMiddleware

from flask import Flask
from raven.contrib.flask import Sentry

import settings
from app.version import __version__

sentry = Sentry()


def create_app(config_name="settings"):
    from app.resources import api

    app = Flask('core')
    app.config.from_object(config_name)

    if settings.DATADOG_ENV:
        TraceMiddleware(
            app,
            tracer,
            service="metis",
            distributed_tracing=True)

    if settings.SENTRY_DSN:
        sentry.init_app(
            app,
            dsn=settings.SENTRY_DSN,
            logging=True,
            level=logging.ERROR)
        sentry.client.release = __version__

    api.init_app(app)

    return app
