from flask import Flask


def create_app(config_name="settings"):
    from app.resources import api

    app = Flask('core')
    app.config.from_object(config_name)

    api.init_app(app)

    return app
