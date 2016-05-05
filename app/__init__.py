import settings
from flask import Flask


def create_app(config_name="settings"):
    from app.resources import api

    app = Flask('core')
    app.config.from_object(config_name)
    app.config['CELERY_BROKER_URL'] = settings.REDIS_URL
    app.config['CELERY_RESULT_BACKEND'] = settings.REDIS_URL
    # celery.conf.update(app.config)
    api.init_app(app)

    return app

