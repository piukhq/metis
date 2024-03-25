from enum import StrEnum


class RetryTypes(StrEnum):
    REMOVE = "remove"
    REDACT = "redact"
    REMOVE_AND_REDACT = "remove_and_redact"
