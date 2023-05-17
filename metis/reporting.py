import logging
from typing import TYPE_CHECKING, cast

from gunicorn.glogging import Logger as GLogger
from loguru import logger

if TYPE_CHECKING:
    from gunicorn.config import Config


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        level: int | str
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            if frame.f_back:
                frame = frame.f_back
            depth += 1

        try:
            # A gunicorn log record contains information in the following format
            # https://docs.gunicorn.org/en/stable/settings.html#access-log-format
            # i.e `X-Azure-Ref` request header is represented as `{x-azure-ref}i`
            extras = {"x_azure_ref": record.args["{x-azure-ref}i"]}
        except Exception:
            extras = {}

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage(), **extras)


# Intercept glogger into loguru
class GunicornAccessFiltering(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        if request_info := cast(str, record.args.get("r")):
            return not any(endpoint in request_info for endpoint in ("/healthz", "/livez", "/readyz", "/metrics"))

        return True


class CustomGunicornLogger(GLogger):
    def setup(self, cfg: "Config") -> None:
        super().setup(cfg)
        self.error_log.handlers = [InterceptHandler()]
        self.access_log.handlers = [InterceptHandler()]
        self.access_log.addFilter(GunicornAccessFiltering())
