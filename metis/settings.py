import logging
import sys

import sentry_sdk
from bink_logging_utils import init_loguru_root_sink
from decouple import Choices, config
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.loguru import LoguruIntegration

from metis.prometheus.logging import metrics_logger
from metis.reporting import InterceptHandler
from metis.utils import ctx
from metis.vault import secrets_from_vault

SECRET_KEY = b"\x00\x8d\xab\x02\x88\\\xc2\x96&\x0b<2n0n\xc9\x19\xec8\xab\xc5\x08N["
ALLOWED_LOG_LEVELS = Choices(("NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"))
ROOT_LOG_LEVEL = config("LOG_LEVEL", default="INFO", cast=ALLOWED_LOG_LEVELS)
JSON_LOGGING = config("JSON_LOGGING", default=True, cast=bool)


def azure_ref_patcher(record: dict):
    if ctx.x_azure_ref:
        record["extra"].update({"x-azure-ref": ctx.x_azure_ref})


init_loguru_root_sink(
    json_logging=JSON_LOGGING, sink_log_level=ROOT_LOG_LEVEL, show_pid=True, custom_patcher=azure_ref_patcher
)

SPREEDLY_BASE_URL = config("SPREEDLY_BASE_URL", default="https://core.spreedly.com/v1")

VOP_SPREEDLY_BASE_URL = config("VOP_SPREEDLY_BASE_URL", default="https://core.spreedly.com/v1")

DEBUG = config("METIS_DEBUG", False)

DEV_HOST = config("DEV_HOST", default="0.0.0.0")
DEV_PORT = config("DEV_PORT", default="5050", cast=int)

TESTING = config("METIS_TESTING", default=False, cast=bool)
PRE_PRODUCTION = config("METIS_PRE_PRODUCTION", default=False, cast=bool)

STUBBED_AMEX_URL = config("STUBBED_AMEX_URL", default="http://pelops")
STUBBED_VOP_URL = config("STUBBED_VOP_URL", default="http://pelops")

HERMES_URL = config("HERMES_URL", default="http://127.0.0.1:5010")
SERVICE_API_KEY = "F616CE5C88744DD52DB628FAD8B3D"

AMQP_URL = config("AMQP_URL", default="amqp://guest:guest@localhost:5672/")
broker_url = AMQP_URL
worker_enable_remote_control = False

TOKEN_SECRET = "8vA/fjVA83(n05LWh7R4'$3dWmVCU"

SENTRY_DSN = config("SENTRY_DSN", default=None)
SENTRY_ENV = config("SENTRY_ENV", default=None)
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENV,
        integrations=[
            CeleryIntegration(),
            LoguruIntegration(),
        ],
    )

POSTGRES_CONNECT_ARGS = {"application_name", "metis"}

AZURE_VAULT_URL = config("AZURE_VAULT_URL", default="")
# Changed from CELERY_ACCEPT_CONTENT due to deprecation
accept_content = ["pickle", "json", "msgpack", "yaml"]


class Secrets:
    # These attributes will contain the secrets
    vop_client_certificate_path = None
    vop_client_key_path = None
    spreedly_visa_receive_token = None
    spreedly_amex_receive_token = None
    spreedly_mastercard_receive_token = None
    vop_user_id = None
    vop_password = None
    spreedly_vop_user_id = None
    spreedly_vop_password = None
    vop_community_code = None
    vop_spreedly_community_code = None
    vop_merchant_group = None
    vop_offerid = None
    amex_client_id = None
    amex_client_secret = None
    spreedly_oauth_username = None
    spreedly_oauth_password = None

    # One entry for each of the above attributes is required for app to start  The secret is stored in the attribute
    # unless file path is declared in which case the secret is saved to the file and the attribute set to the file path
    SECRETS_DEF = {
        "vop_client_certificate_path": {
            "vault_name": "vop-clientCert",
            "file_path": "/tmp/vop_client_certificate.pem",
        },
        "vop_client_key_path": {
            "vault_name": "vop-clientKey",
            "file_path": "/tmp/vop_client_key.pem",
        },
        "spreedly_visa_receive_token": {"vault_name": "spreedly-visaReceiveToken"},
        "spreedly_amex_receive_token": {"vault_name": "spreedly-amexReceiveToken"},
        "spreedly_mastercard_receive_token": {"vault_name": "spreedly-mastercardReceiveToken"},
        "vop_community_code": {"vault_name": "vop-communityCode"},
        "vop_spreedly_community_code": {"vault_name": "vop-spreedlyCommunityCode"},
        "vop_offerid": {"vault_name": "vop-offerId"},
        "vop_user_id": {"vault_name": "vop-authUserId"},
        "vop_password": {"vault_name": "vop-authPassword"},
        "spreedly_vop_user_id": {"vault_name": "spreedly-vopAuthUserId"},
        "spreedly_vop_password": {"vault_name": "spreedly-vopAuthPassword"},
        "vop_merchant_group": {"vault_name": "vop-merchantGroup"},
        "amex_client_id": {"vault_name": "amex-clientId"},
        "amex_client_secret": {"vault_name": "amex-clientSecret"},
        "spreedly_oauth_username": {"vault_name": "spreedly-oAuthUsername"},
        "spreedly_oauth_password": {"vault_name": "spreedly-oAuthPassword"},
    }


# Prometheus settings
PROMETHEUS_LOG_LEVEL = config("PROMETHEUS_LOG_LEVEL", default="INFO", cast=ALLOWED_LOG_LEVELS)
PUSH_PROMETHEUS_METRICS = config("PUSH_PROMETHEUS_METRICS", default=True, cast=bool)
PROMETHEUS_PUSH_GATEWAY = "http://localhost:9100"
PROMETHEUS_JOB = "metis"

PROMETHEUS_TESTING = any("test" in arg for arg in sys.argv)

# Configure log level for prometheus logger
metrics_logger.setLevel(level=PROMETHEUS_LOG_LEVEL)
# funnel all loggers into loguru.
logging.basicConfig(handlers=[InterceptHandler()])

if AZURE_VAULT_URL:
    secrets_from_vault()
else:
    Secrets.vop_client_certificate_path = None
    Secrets.vop_client_key_path = None
    Secrets.spreedly_visa_receive_token = "visa"
    Secrets.spreedly_amex_receive_token = "amex"
    Secrets.spreedly_mastercard_receive_token = "mastercard"
    Secrets.vop_user_id = "test"
    Secrets.vop_password = "test"
    Secrets.spreedly_vop_user_id = "test"
    Secrets.spreedly_vop_password = "test"
    Secrets.vop_community_code = "community_code"
    Secrets.vop_spreedly_community_code = "spreedly_code"
    Secrets.vop_merchant_group = "test_merch"
    Secrets.vop_offerid = "12345"
    Secrets.amex_client_id = "test"
    Secrets.amex_client_secret = "test"
    Secrets.spreedly_oauth_username = "test"
    Secrets.spreedly_oauth_password = "test"
