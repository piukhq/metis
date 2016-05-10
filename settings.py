from environment import env_var, read_env

read_env()

TESTING = env_var("METIS_TESTING", False)

REDIS_URL = env_var("REDIS_URI", "redis://localhost:6379/0")


AMEX_RECEIVER = "spreedly_amex_token"
VISA_RECEIVER = "spreedly_visa_token"
MASTERCARD_RECEIVER = "spreedly_mastercard_token"