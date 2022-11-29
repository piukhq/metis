import jwt
from flask import jsonify
from flask_restful import abort, request

import settings

HTTP_HEADER_ENCODING = "iso-8859-1"


def parse_token(auth_header):
    """
    Verifies that an access-token is valid and meant for this app.
    """
    auth = auth_header.encode(HTTP_HEADER_ENCODING).split()
    if not auth or auth[0].lower() != b"token":
        return None

    token = auth[1].decode()

    if token == settings.SERVICE_API_KEY:
        return True

    token_contents = jwt.decode(token, settings.TOKEN_SECRET, algorithms=["HS256"])

    return token_contents


def authorized(fn):
    """Decorator that checks that requests
    contain an id-token in the request header.
    """

    def _wrap(*args, **kwargs):
        if "Authorization" not in request.headers:
            # Unauthorized
            abort(401)
            return None

        try:
            parse_token(request.headers["Authorization"])
        except jwt.DecodeError:
            response = jsonify(message="Token is invalid")
            response.status_code = 401
            return response
        except jwt.ExpiredSignature:
            response = jsonify(message="Token has expired")
            response.status_code = 401
            return response

        return fn(*args, **kwargs)

    return _wrap
