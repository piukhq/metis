import importlib

from app.active import AGENTS


def resolve_agent(name):
    class_path = AGENTS[name]
    module_name, class_name = class_path.split(".")
    module = importlib.import_module("app.agents.{}".format(module_name))
    return getattr(module, class_name)
