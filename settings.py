from environment import env_var, read_env
import os

SECRET_KEY = b'\x00\x8d\xab\x02\x88\\\xc2\x96&\x0b<2n0n\xc9\x19\xec8\xab\xc5\x08N['

read_env()

APP_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
DEBUG = env_var("ZEUS_DEBUG", False)

DEV_HOST = env_var("DEV_HOST", "0.0.0.0")
DEV_PORT = env_var("DEV_PORT", "5050")

TESTING = env_var("METIS_TESTING", False)

REDIS_URL = env_var("REDIS_URI", "redis://localhost:6379/0")


AMEX_RECEIVER = "spreedly_amex_token"
VISA_RECEIVER = "spreedly_visa_token"
MASTERCARD_RECEIVER = "spreedly_mastercard_token"
