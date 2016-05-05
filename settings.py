from environment import env_var, read_env

read_env()

REDIS_URL = env_var("REDIS_URI", "redis://localhost:6379/0")

TEST_RECEIVER = "aDwu4ykovZVe7Gpto3rHkYWI5wI"
AMEX_RECEIVER = "spreedly_amex_token"
VISA_RECEIVER = "spreedly_visa_token"
MASTERCARD_RECEIVER = "spreedly_mastercard_token"