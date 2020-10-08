from enum import Enum


class ActionCode(Enum):
    ADD = 'A'
    DELETE = 'D'
    REACTIVATE = 'R'
    ACTIVATE_MERCHANT = 'M'
    DEACTIVATE_MERCHANT = 'X'
