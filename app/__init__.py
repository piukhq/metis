import logging
from flask import Flask
from raven.contrib.flask import Sentry
from settings import SENTRY_DSN

sentry = Sentry()


def create_app(config_name="settings"):
    from app.resources import api

    app = Flask('core')
    app.config.from_object(config_name)
    if SENTRY_DSN:
        sentry.init_app(app, dsn=SENTRY_DSN, logging=True, level=logging.ERROR)

    api.init_app(app)

    return app
