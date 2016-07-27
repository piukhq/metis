import unittest
import settings
from app.agents.spreedly import Spreedly
from app.services import create_receiver, create_sftp_receiver, end_site_receiver


class TestServices(unittest.TestCase):
    def test_create_receiver(self):
        resp = create_receiver('http://latestserver.com')
        self.assertTrue(resp.status_code == 201)
        self.assertIn('token', resp.text)

    def test_end_site_receiver(self):
        settings.TESTING = True
        payment_method_token = '3rkN9aJFfNEjvr2LqYZE4606hgG'
        resp = end_site_receiver('mastercard', payment_method_token)
        self.assertTrue(resp.status_code == 200)

    def test_create_visa_sftp_receiver(self):
        sftp_details = {'receiver_type': 'test', 'hostnames': 'sftp://178.238.141.18',
                        'username': 'spreedlyftp', 'password': 'Ohpov9Sae2ge'}

        resp = create_sftp_receiver(sftp_details)
        self.assertTrue(resp.status_code == 201)
        self.assertIn('token', resp.text)

    def test_spreedly_save(self):
        log = """    <transactions>
      <transaction>
        <amount type="integer">100</amount>
        <on_test_gateway type="boolean">false</on_test_gateway>
        <created_at type="datetime">2012-09-10T20:35:10Z</created_at>
        <updated_at type="datetime">2012-09-10T20:35:11Z</updated_at>
        <currency_code>USD</currency_code>
        <succeeded type="boolean">true</succeeded>
        <state>succeeded</state>
        <token>5AG4P7FPjlfIA6aED6AgZvUEehx</token>
        <transaction_type>OffsitePurchase</transaction_type>
        <order_id nil="true"></order_id>
        <ip nil="true"></ip>
        <callback_url>http://example.com/handle_callback</callback_url>
        <signed>
          <signature>b81436daf0d695404c5bf7a2aecf049d460bb6e1</signature>
          <fields>amount callback_url created_at currency_code ip on_test_gateway order_id state succeeded token transaction_type updated_at</fields>
          <algorithm>sha1</algorithm>
        </signed>
      </transaction>
    </transactions>"""  # noqa
        # noqa comment prevents flake8 checking the previous string.

        settings.SPREEDLY_SIGNING_SECRET = 'RKOCG5D8D3fZxDSg504D0IxU2XD4Io5VXmyzdCtTivHFTTSylzM2ZzTWFwVH4ucG'
        s = Spreedly()
        result = s.save(log)
        self.assertTrue(result)
