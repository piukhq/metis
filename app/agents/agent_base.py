import requests
import settings

# Username and password from Spreedly site - Loyalty Angels environments
username = 'Yc7xn3gDP73PPOQLEB2BYpv31EV' if settings.TESTING else '1Lf7DiKgkcx5Anw7QxWdDxaKtTa'
password = '4m8tVKWHvakjhfBXnRVDbfkOArB9NvAyo9U6lWtVulb2thuI6T439blRbQWGwQcH'


class AgentBase:

    @staticmethod
    def post_request(url, header, request_data):
        settings.logger.info('POST Spreedly request to {}'.format(url))
        resp = requests.post(url, auth=(username, password), headers=header, data=request_data)
        settings.logger.info('Spreedly POST response: {}'.format(resp.text))
        return resp
