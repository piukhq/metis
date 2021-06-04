from prometheus_client import Counter, CollectorRegistry, Histogram, push_to_gateway
import settings


NAMESPACE = 'metis'
STATUS_FAILED = "Failed"
STATUS_SUCCESS = "Success"
STATUS_OTHER_RETRY = "Retry-Other"
STATUS_TIMEOUT_RETRY = "Retry-Timeout"

registry = CollectorRegistry()

status_counter = Counter(
    name="retain_status_by_provider",
    documentation="Count for retain status by provider.",
    labelnames=("provider", "status", ),
    namespace=NAMESPACE,
)

spreedly_retain_processing_seconds_histogram = Histogram(
    name="spreedly_retain_processing_seconds_histogram",
    documentation="Response time for Spreedly retain.",
    labelnames=("provider", "status", ),
    buckets=(5.0, 10.0, 30.0, 300.0, 3600.0, 43200.0, 86400.0, float("inf")),
    namespace=NAMESPACE,
)

vop_activations_counter = Counter(
    name="visa_vop_activations",
    documentation="Count for Visa VOP activations.",
    labelnames=("status",),
    namespace=NAMESPACE,
)

vop_activations_processing_seconds_histogram = Histogram(
    name="vop_activation_processing_seconds_histogram",
    documentation="Response time for VOP PLL activation.",
    labelnames=("response_status_code",),
    buckets=(5.0, 10.0, 30.0, 300.0, 3600.0, 43200.0, 86400.0, float("inf")),
    namespace=NAMESPACE,
)

vop_deactivations_counter = Counter(
    name="visa_vop_deactivations",
    documentation="Count for Visa VOP deactivations.",
    labelnames=("status",),
    namespace=NAMESPACE,
)

vop_deactivations_processing_seconds_histogram = Histogram(
    name="vop_deactivation_processing_seconds_histogram",
    documentation="Response time for VOP PLL deactivations.",
    labelnames=("response_status_code",),
    buckets=(5.0, 10.0, 30.0, 300.0, 3600.0, 43200.0, 86400.0, float("inf")),
    namespace=NAMESPACE,
)

# Celery specific metrics

payment_card_enrolment_reponse_time_histogram = Histogram(
    name="card_enrolment_response_time",
    documentation="Response time for payment card enrolments.",
    labelnames=("provider", "status", ),
    buckets=(5.0, 10.0, 30.0, 300.0, 3600.0, 43200.0, 86400.0, float("inf")),
    namespace=NAMESPACE,
    registry=registry
)

payment_card_enrolment_counter = Counter(
    name="card_enrolment_counter",
    documentation="Total cards enrolled ",
    labelnames=("provider", "status", ),
    namespace=NAMESPACE,
    registry=registry
)

unenrolment_counter = Counter(
    name="unenrolment_counter",
    documentation="Count for unenrolments.",
    labelnames=("provider", "status"),
    namespace=NAMESPACE,
    registry=registry
)

unenrolment_response_time_histogram = Histogram(
    name="unenrolment_response_time",
    documentation="Response time for payment card unenrolments.",
    labelnames=("provider", "status", ),
    buckets=(5.0, 10.0, 30.0, 300.0, 3600.0, 43200.0, 86400.0, float("inf")),
    namespace=NAMESPACE,
    registry=registry
)

mastercard_reactivate_counter = Counter(
    name="total_mastercard_spreedly_reactivations",
    documentation="Total Mastercard Spreedly reactivations.",
    labelnames=("status",),
    namespace=NAMESPACE,
    registry=registry
)

mastercard_reactivate_response_time_histogram = Histogram(
    name="mastercard_reactivate_spreedly_response_time",
    documentation="Mastercard reactivate Spreedly response time.",
    labelnames=("status",),
    buckets=(5.0, 10.0, 30.0, 300.0, 3600.0, 43200.0, 86400.0, float("inf")),
    namespace=NAMESPACE,
    registry=registry
)


def push_metrics(pid):
    if not settings.PROMETHEUS_TESTING:
        push_to_gateway(
            settings.PROMETHEUS_PUSH_GATEWAY,
            job=settings.PROMETHEUS_JOB,
            registry=registry,
            grouping_key={"celery": str(pid)}
        )
