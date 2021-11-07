from flask import Flask

from prometheus import init_metrics_collection


def create_app(config_name="settings"):
    from app.resources import api

    app = Flask("core")
    app.config.from_object(config_name)

    api.init_app(app)

    init_metrics_collection()

    return app
