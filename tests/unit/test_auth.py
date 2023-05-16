from unittest import TestCase

from metis.auth import parse_token

auth_key = (
    "Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL"
    "CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU"
)


class TestAuth(TestCase):
    def test_validate_user_none(self):
        result = parse_token("")
        self.assertEqual(result, None)

    def test_validate_user(self):
        result = parse_token(auth_key)
        self.assertEqual(result["sub"], 32)

    def test_service_auth(self):
        result = parse_token("Token F616CE5C88744DD52DB628FAD8B3D")
        self.assertTrue(result)
