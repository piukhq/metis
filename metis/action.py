from enum import StrEnum


class ActionCode(StrEnum):
    ADD = "A"
    DELETE = "D"
    REACTIVATE = "R"
    ACTIVATE_MERCHANT = "M"
    DEACTIVATE_MERCHANT = "X"
