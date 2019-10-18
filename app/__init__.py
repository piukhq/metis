import logging

from flask import Flask

import settings
from app.version import __version__


def create_app(config_name="settings"):
    from app.resources import api

    app = Flask('core')
    app.config.from_object(config_name)

    api.init_app(app)

    return app
