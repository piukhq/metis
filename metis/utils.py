import importlib
import threading

ACTIVE_AGENTS = {"mastercard": "mastercard.MasterCard", "amex": "amex.Amex", "visa": "visa_offers.Visa"}


def resolve_agent(name):
    class_path = ACTIVE_AGENTS[name]
    module_name, class_name = class_path.split(".")
    module = importlib.import_module(f"metis.agents.{module_name}")
    return getattr(module, class_name)


class _Context:
    """Used for storing context data for logging purposes"""

    def __init__(self) -> None:
        self._tls = threading.local()

    @property
    def x_azure_ref(self) -> str | None:
        return getattr(self._tls, "x_azure_ref", None)

    @x_azure_ref.setter
    def x_azure_ref(self, value: str) -> None:
        self._tls.x_azure_ref = value


ctx = _Context()
