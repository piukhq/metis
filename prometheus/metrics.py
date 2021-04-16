from prometheus_client import Counter, CollectorRegistry, Histogram


NAMESPACE = 'metis'
STATUS_FAILED = "Failed"
STATUS_SUCCESS = "Success"

registry = CollectorRegistry()

status_counter = Counter(
    name="retain_status_by_provider",
    documentation="Count for retain status by provider.",
    labelnames=("provider", "status",),
    namespace=NAMESPACE,
)

spreedly_retain_processing_seconds_histogram = Histogram(
    name="spreedly_retain_processing_seconds_histogram",
    documentation="Response time for Spreedly retain.",
    labelnames=("provider", "status"),
    buckets=(5.0, 10.0, 30.0, 300.0, 3600.0, 43200.0, 86400.0, float("inf")),
    namespace=NAMESPACE,
)
