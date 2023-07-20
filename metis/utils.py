import importlib
import threading

from metis.active import AGENTS


def resolve_agent(name):
    class_path = AGENTS[name]
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
