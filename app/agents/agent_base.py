import requests
import settings

# Username and password from Spreedly site - Loyalty Angels environments
username = settings.Secrets.spreedly_oauth_username
password = settings.Secrets.spreedly_oauth_password


class AgentBase:

    @staticmethod
    def post_request(url, header, request_data):
        settings.logger.info('POST Spreedly request to {}'.format(url))
        resp = requests.post(url, auth=(username, password), headers=header, data=request_data)
        settings.logger.info('Spreedly POST response: {}'.format(resp.text))
        return resp
