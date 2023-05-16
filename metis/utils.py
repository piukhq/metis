import importlib

from metis.active import AGENTS


def resolve_agent(name):
    class_path = AGENTS[name]
    module_name, class_name = class_path.split(".")
    module = importlib.import_module(f"metis.agents.{module_name}")
    return getattr(module, class_name)
