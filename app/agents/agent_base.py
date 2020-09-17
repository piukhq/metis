# Username and password from Spreedly site - Loyalty Angels environments
from app.services import send_request


class AgentBase:

    @classmethod
    def post_request(cls, url, header, request_data):
        return send_request('POST', url, header, request_data)
