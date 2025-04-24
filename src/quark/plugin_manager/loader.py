import importlib
from typing import Protocol


class PluginInterface(Protocol):
    """Every plugin must implement this interface.

    A valid register() function must register each of its modules with the QUARK plugin manager by calling
    factory.register() for each module. The register() function must be available at the top level of the module. This
    is best achieved by providing it in the __init__.py file at the top level of the plugin.

    For more information, see the documentation or use the QUARK plugin template:
    https://github.com/QUARK-framework/QUARK-plugin-template
    """

    @staticmethod
    def register() -> None:
        pass


def import_module(plugin_file: str) -> PluginInterface:
    return importlib.import_module(plugin_file) # pyright: ignore


def load_plugins(plugin_files: list[str]) -> None:
    for plugin_file in plugin_files:
        module = import_module(plugin_file)
        module.register()
