import graypy
import logging
import os
from environment import env_var, read_env


SECRET_KEY = b'\x00\x8d\xab\x02\x88\\\xc2\x96&\x0b<2n0n\xc9\x19\xec8\xab\xc5\x08N['

read_env()

SPREEDLY_SIGNING_SECRET = env_var('SPREEDLY_SIGNING_SECRET',
                                  '4UWSUEtjUaANznj9mtCz0OCqduHj1iyiQeYTz4q6XIgkRkYTHXiu2xT0k72awYCa')
SPREEDLY_BASE_URL = env_var('SPREEDLY_RECEIVER_URL', 'https://core.spreedly.com/v1')

APP_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
DEBUG = env_var("METIS_DEBUG", False)

DEV_HOST = env_var("DEV_HOST", "0.0.0.0")
DEV_PORT = env_var("DEV_PORT", "5050")

TESTING = env_var("METIS_TESTING", False)

HERMES_URL = env_var("HERMES_URL", 'http://127.0.0.1:5010')
SERVICE_API_KEY = 'F616CE5C88744DD52DB628FAD8B3D'

# celery config
BROKER_URL = env_var('CELERY_BROKER_URL', 'redis://localhost:6379')
# if you need to read task results, uncomment and set this
# CELERY_RESULT_BACKEND = env_var('CELERY_RESULT_BACKEND', 'redis://localhost:6379')

RABBITMQ_HOST = env_var('RABBITMQ_HOST', '192.168.1.53')
RABBITMQ_USER = env_var('RABBITMQ_USER', 'guest')
RABBITMQ_PASS = env_var('RABBITMQ_PASS', 'guest')

# how many card enrolments can we fit in a single file, and how many files can we send per day?
CARDS_PER_FILE = 80000
FILES_PER_DAY = 99

# how long to wait in between each file transfer to spreedly
SPREEDLY_SEND_DELAY = 30

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
logging.basicConfig(format='%(process)s %(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('metis_logger')
logger.setLevel(logging.DEBUG)
tmp_logger = False

GRAYLOG_HOST = env_var('GRAYLOG_HOST')
if GRAYLOG_HOST:
    GRAYLOG_PORT = int(env_var('GRAYLOG_PORT'))
    handler = graypy.GELFHandler(GRAYLOG_HOST, GRAYLOG_PORT)
    logger.addHandler(handler)
elif tmp_logger:
    handler_loc = logging.FileHandler('/var/tmp/metis_tmp.log')
    logger.addHandler(handler_loc)

SENTRY_DSN = env_var("METIS_SENTRY_DSN")

PONTUS_DATABASE = env_var('PONTUS_DATABASE', 'pontus')
PONTUS_USER = env_var('PONTUS_USER', 'laadmin')
PONTUS_PASSWORD = env_var('PONTUS_PASSWORD', '!^LoyaltyDev2015')
PONTUS_HOST = env_var('PONTUS_HOST', '192.168.1.53')
PONTUS_PORT = env_var('PONTUS_PORT', '5432')


# Store VISA private key separately from other keys
VISA_SOURCE_FILES_DIR = env_var('VISA_SOURCE_FILES_DIR', '../visa_handback_files')
VISA_KEYRING_DIR = env_var('VISA_KEYRING_DIR', '~/.gnupg')
VISA_ARCHIVE_DIR = env_var('VISA_ARCHIVE_DIR', '/tmp/archive/visa')
VISA_ENCRYPTED_FILE_EXTENSION = env_var('VISA_ENCRYPTED_FILE_EXTENSION', 'pgp')

SLACK_API_TOKEN = 'xoxb-119487439522-Lsefc6ykOx3RIXC89WN8wx3h'
