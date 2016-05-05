import unittest
from app.services import create_receiver, end_site_receiver
from settings import TEST_RECEIVER


class TestServices(unittest.TestCase):
    def test_create_receiver(self):
        resp = create_receiver('http://latestserver.com')
        self.assertTrue(resp.status_code == 201)
        self.assertIn('token', resp.text)

    def test_end_site_receiver(self):
        payment_method_token = '3rkN9aJFfNEjvr2LqYZE4606hgG'
        resp = end_site_receiver('http://latestserver.com/post.php', TEST_RECEIVER, payment_method_token)
        self.assertTrue(resp.status_code == 200)
