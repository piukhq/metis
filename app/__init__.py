from flask import Flask
from vault import secrets_from_vault


def create_app(config_name="settings"):
    from app.resources import api

    app = Flask('core')
    app.config.from_object(config_name)

    api.init_app(app)
    secrets_from_vault()
    return app
