import logging
import os
import threading
import time
import urllib.error

from prometheus_client import push_to_gateway
from prometheus_client.registry import REGISTRY

import settings

logger = logging.getLogger("prometheus")
logger.setLevel(settings.PROMETHEUS_LOG_LEVEL)


class PrometheusPushThread(threading.Thread):
    SLEEP_INTERVAL = 30
    PUSH_TIMEOUT = 3  # PushGateway should be running in the same pod

    def __init__(self, pid: str):
        # Grouping key should not need pod id as prometheus
        # should tag that itself
        self.grouping_key = {"pid": pid}
        super().__init__()

    def run(self):
        time.sleep(10)
        while True:
            now = time.time()
            try:
                push_to_gateway(
                    gateway=settings.PROMETHEUS_PUSH_GATEWAY,
                    job=settings.PROMETHEUS_JOB,
                    registry=REGISTRY,
                    grouping_key=self.grouping_key,
                    timeout=self.PUSH_TIMEOUT,
                )
                logger.debug("Pushed metrics to gateway")
            except (ConnectionRefusedError, urllib.error.URLError):
                logger.warning("Failed to push metrics, connection refused")
            except Exception as err:
                logger.exception("Caught exception whilst posting metrics", exc_info=err)

            remaining = self.SLEEP_INTERVAL - (time.time() - now)
            if remaining > 0:
                time.sleep(remaining)


def init_metrics_collection():
    if not settings.PROMETHEUS_TESTING:
        logger.info("Configuring prometheus metrics pusher")
        process_id = str(os.getpid())
        thread = PrometheusPushThread(process_id)
        thread.daemon = True
        thread.start()
        logger.info("Prometheus push thread started")
    else:
        logger.info("Prometheus push thread not initialised as this is a test")