import logging
import sys
from typing import ClassVar, Literal

import sentry_sdk
from bink_logging_utils import init_loguru_root_sink
from pydantic import field_validator
from pydantic_settings import BaseSettings
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.loguru import LoguruIntegration

from metis.prometheus.logging import metrics_logger
from metis.reporting import InterceptHandler
from metis.utils import ctx

AllowedLogLevelsType = Literal["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    SECRET_KEY: ClassVar[bytes] = b"\x00\x8d\xab\x02\x88\\\xc2\x96&\x0b<2n0n\xc9\x19\xec8\xab\xc5\x08N["
    LOG_LEVEL: AllowedLogLevelsType = "INFO"
    JSON_LOGGING: bool = True

    SPREEDLY_BASE_URL: str = "https://core.spreedly.com/v1"
    VOP_SPREEDLY_BASE_URL: str = "https://core.spreedly.com/v1"

    METIS_DEBUG: bool = False

    DEV_HOST: str = "localhost"
    DEV_PORT: int = 5050

    METIS_TESTING: bool = False
    METIS_PRE_PRODUCTION: bool = False

    STUBBED_AMEX_URL: str = "http://pelops"
    STUBBED_VOP_URL: str = "http://pelops"

    HERMES_URL: str = "http://127.0.0.1:5010"
    SERVICE_API_KEY: ClassVar[str] = "F616CE5C88744DD52DB628FAD8B3D"

    CELERY_BROKER_URL: str = "amqp://guest:guest@localhost:5672/"

    TOKEN_SECRET: ClassVar[str] = "8vA/fjVA83(n05LWh7R4'$3dWmVCU"

    SENTRY_DSN: str | None = None
    SENTRY_ENV: str | None = None

    AZURE_VAULT_URL: str = ""

    # Prometheus settings
    PROMETHEUS_LOG_LEVEL: AllowedLogLevelsType = "INFO"
    PUSH_PROMETHEUS_METRICS: bool = True
    PROMETHEUS_PUSH_GATEWAY: ClassVar[str] = "http://localhost:9100"
    PROMETHEUS_JOB: ClassVar[str] = "metis"

    PROMETHEUS_TESTING: bool = False

    @field_validator("PROMETHEUS_TESTING")
    @classmethod
    def testing_validator(cls, value: bool) -> bool:
        return value or any("test" in arg for arg in sys.argv)

    class Config:
        case_sensitive = True
        # env var settings priority ie priority 1 will override priority 2:
        # 1 - env vars already loaded (ie the one passed in by kubernetes)
        # 2 - env vars read from .env file
        # 3 - values assigned directly in the Settings class
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def azure_ref_patcher(record: dict) -> None:
    if ctx.x_azure_ref:
        record["extra"].update({"x-azure-ref": ctx.x_azure_ref})


init_loguru_root_sink(
    json_logging=settings.JSON_LOGGING,
    sink_log_level=settings.LOG_LEVEL,
    show_pid=True,
    custom_patcher=azure_ref_patcher,
)

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENV,
        integrations=[
            CeleryIntegration(),
            LoguruIntegration(),
        ],
    )


# Configure log level for prometheus logger
metrics_logger.setLevel(level=settings.PROMETHEUS_LOG_LEVEL)
# funnel all loggers into loguru.
logging.basicConfig(handlers=[InterceptHandler()])
