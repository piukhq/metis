import arrow
import requests
import settings

# Username and password from Spreedly site - Loyalty Angels environments
password = '94iV3Iyvky86avhdjLgIh0z9IFeB0pw4cZvu64ufRgaur46mTM4xepsPDOdxVH51'
# Production
username = '1Lf7DiKgkcx5Anw7QxWdDxaKtTa'
receiver_base_url = settings.SPREEDLY_RECEIVER_URL
# Testing
# Username used for MasterCard and Visa testing only
# username = 'Yc7xn3gDP73PPOQLEB2BYpv31EV'


class AgentBase:
    @staticmethod
    def post_request(url, header, request_data):
        settings.logger.info('{} POST Spreedly request to {}'.format(arrow.now(), url))
        resp = requests.post(url, auth=(username, password), headers=header, data=request_data)
        return resp
