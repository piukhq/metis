import settings

# Username and password from Spreedly site - Loyalty Angels environments
from app.services import send_request

username = settings.Secrets.spreedly_oauth_username
password = settings.Secrets.spreedly_oauth_password


class AgentBase:

    @classmethod
    def post_request(cls, url, header, request_data):
        return send_request('POST', url, header, request_data)
