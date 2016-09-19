import graypy
import logging
import os
from environment import env_var, read_env


SECRET_KEY = b'\x00\x8d\xab\x02\x88\\\xc2\x96&\x0b<2n0n\xc9\x19\xec8\xab\xc5\x08N['

read_env()

SPREEDLY_SIGNING_SECRET = env_var('SPREEDLY_SIGNING_SECRET',
                                  '4UWSUEtjUaANznj9mtCz0OCqduHj1iyiQeYTz4q6XIgkRkYTHXiu2xT0k72awYCa')

APP_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
DEBUG = env_var("ZEUS_DEBUG", False)

DEV_HOST = env_var("DEV_HOST", "0.0.0.0")
DEV_PORT = env_var("DEV_PORT", "5050")

TESTING = env_var("METIS_TESTING", False)

HERMES_URL = env_var("HERMES_URL", 'http://127.0.0.1:5010')
SERVICE_API_KEY = 'F616CE5C88744DD52DB628FAD8B3D'

AMEX_RECEIVER = "spreedly_amex_token"
VISA_RECEIVER = "spreedly_visa_token"
MASTERCARD_RECEIVER = "spreedly_mastercard_token"

# celery config
BROKER_URL = env_var('CELERY_BROKER_URL', 'redis://localhost:6379')
# if you need to read task results, uncomment and set this
# CELERY_RESULT_BACKEND = env_var('CELERY_RESULT_BACKEND', 'redis://localhost:6379')

TOKEN_SECRET = "8vA/fjVA83(n05LWh7R4'$3dWmVCU"

# -------------------------------------------------------------------------------
# Cassandra cluster
# -------------------------------------------------------------------------------

# dev machine
CASSANDRA_CLUSTER = ('192.168.1.60', '192.168.1.61',  '192.168.1.62')
# local machine
# CASSANDRA_CLUSTER = ('127.0.0.1', '127.0.0.2', '127.0.0.3')
# aws deployment
# CASSANDRA_CLUSTER=(['unknown', 'unknown', 'unknown')

CASSANDRA_TRANSACTION_KEYSPACE = 'lakeyspace'

# Logging settings
# Use Graylog when setup, temporarily use local log files.
logger = logging.getLogger('metis_logger')
logger.setLevel(logging.DEBUG)
tmp_logger = True

GRAYLOG_HOST = env_var('GRAYLOG_HOST')
if GRAYLOG_HOST:
    handler = graypy.GELFHandler(GRAYLOG_HOST, 12201)
    logger.addHandler(handler)
elif tmp_logger:
    handler_loc = logging.FileHandler('/var/tmp/metis_tmp.log')
    logger.addHandler(handler_loc)
