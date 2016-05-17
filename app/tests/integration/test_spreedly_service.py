import unittest
import settings
from app.services import create_receiver, end_site_receiver


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
