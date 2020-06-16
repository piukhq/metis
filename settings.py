import graypy
import logging
import os
import sentry_sdk
from environment import env_var, read_env
from sentry_sdk.integrations.celery import CeleryIntegration
from vault import secrets_from_vault

SECRET_KEY = b'\x00\x8d\xab\x02\x88\\\xc2\x96&\x0b<2n0n\xc9\x19\xec8\xab\xc5\x08N['

read_env()

SPREEDLY_SIGNING_SECRET = env_var('SPREEDLY_SIGNING_SECRET',
                                  '4UWSUEtjUaANznj9mtCz0OCqduHj1iyiQeYTz4q6XIgkRkYTHXiu2xT0k72awYCa')
SPREEDLY_BASE_URL = env_var('SPREEDLY_BASE_URL', 'https://core.spreedly.com/v1')

APP_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
DEBUG = env_var("METIS_DEBUG", False)

DEV_HOST = env_var("DEV_HOST", "0.0.0.0")
DEV_PORT = env_var("DEV_PORT", "5050")

TESTING = env_var("METIS_TESTING", False)
PRE_PRODUCTION = env_var("METIS_PRE_PRODUCTION", False)

STUBBED_VOP_URL = env_var("STUBBED_VOP_URL", '')

HERMES_URL = env_var("HERMES_URL", 'http://127.0.0.1:5010')
SERVICE_API_KEY = 'F616CE5C88744DD52DB628FAD8B3D'

REDIS_HOST = env_var('REDIS_HOST', 'localhost')
REDIS_PORT = env_var('REDIS_PORT', 6379)
REDIS_PASS = env_var('REDIS_PASS', '')
REDIS_TLS = env_var('REDIS_TLS', False)
REDIS_DB = env_var('REDIS_DB', 0)


if env_var('CELERY_BROKER_URL'):
    BROKER_URL = env_var('CELERY_BROKER_URL')
else:
    if REDIS_TLS:
        BROKER_URL = f'rediss://:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}?ssl_cert_reqs=optional'
    else:
        BROKER_URL = f'redis://:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

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

SENTRY_DSN = env_var("SENTRY_DSN", None)
SENTRY_ENV = env_var("SENTRY_ENV", None)
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENV,
        integrations=[
            CeleryIntegration()
        ]
    )

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

TEAMS_WEBHOOK_URL = env_var('TEAMS_WEBHOOK_URL')

AZURE_VAULT_URL = env_var("AZURE_VAULT_URL", "http://127.0.0.1:8200")
VAULT_SECRETS_PATH = env_var("VAULT_SECRETS_PATH", "/v1/secret")
CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack', 'yaml']


class Secrets:
    # These attributes will contain the secrets
    vop_client_certificate_path = None
    vop_client_key_path = None
    spreedly_receive_token = None
    vop_user_id = None
    vop_password = None
    spreedly_vop_user_id = None
    spreedly_vop_password = None
    vop_community_code = None
    vop_spreedly_community_code = None
    vop_merchant_group = None
    vop_offerid = None

    # One entry for each of the above attributes is required for app to start  The secret is stored in the attribute
    # unless file path is declared in which case the secret is saved to the file and the attribute set to the file path
    SECRETS_DEF = {
        "vop_client_certificate_path": {
            "vault_name": "/vop/clientCert",
            "file_path": "/tmp/vop_client_certificate.pem",
        },
        "vop_client_key_path": {
            "vault_name": "/vop/clientKey",
            "file_path": "/tmp/vop_client_key.pem",
        },
        "spreedly_receive_token": {
            "vault_name": "/spreedly/receiveToken"
        },
        "vop_community_code": {
            "vault_name": "/vop/communityCode"
        },
        "vop_spreedly_community_code": {
            "vault_name": "/vop/spreedlyCommunityCode"
        },
        "vop_offerid": {
            "vault_name": "/vop/offerId"
        },
        "vop_user_id": {
            "vault_name": "/vop/authUserId"
        },
        "vop_password": {
            "vault_name": "/vop/authPassword"
        },
        "spreedly_vop_user_id": {
            "vault_name": "/spreedly/vopAuthUserId"
        },
        "spreedly_vop_password": {
            "vault_name": "/spreedly/vopAuthPassword"
        },
        "vop_merchant_group": {
            "vault_name": "/vop/merchantGroup"
        }
    }


secrets_from_vault()
