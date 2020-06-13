from flask import Flask
from app.agents.secrets import Secret


def create_app(config_name="settings"):
    from app.resources import api

    app = Flask('core')
    app.config.from_object(config_name)

    api.init_app(app)
    Secret.load_from_vault()
    return app
