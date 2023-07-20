from werkzeug.datastructures import EnvironHeaders

from metis.utils import ctx


class AzureRefMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        headers = EnvironHeaders(environ)
        ctx.x_azure_ref = headers.get("X-Azure-Ref")
        return self.app(environ, start_response)
