import importlib
from typing import Protocol

class PluginInterface(Protocol):

    @staticmethod
    def register() -> None:
        ...

def import_module(plugin_file: str) -> PluginInterface:
    return importlib.import_module(plugin_file) # type: ignore


def load_plugins(plugin_files: list[str]) -> None:
    for plugin_file in plugin_files:
        module = import_module(plugin_file)
        module.register()
