from app.services import send_request


class AgentBase:

    @staticmethod
    def post_request(url, header, request_data):
        return send_request('POST', url, header, request_data)
