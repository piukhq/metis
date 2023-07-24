from flask import Flask

from metis.middlware import AzureRefMiddleware
from metis.prometheus import init_metrics_collection


def create_app(config_name="metis.settings"):
    from metis.resources import api

    app = Flask("core")
    app.wsgi_app = AzureRefMiddleware(app.wsgi_app)
    app.config.from_object(config_name)

    api.init_app(app)

    init_metrics_collection()

    return app
