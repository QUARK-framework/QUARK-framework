from collections.abc import Callable
from typing import Any

from quark.core import Core

plugin_creation_funcs: dict[str, Callable[..., Core]] = {}


def register(plugin_type: str, creator_fn: Callable[..., Core]) -> None:
    """Register a module with the factory.

    To use a module in the pipeline specification of a config file, it has to be registered to the factory by the plugin
    it is included in. For each plugin given in the config file, quark's plugin loader will call the plugin's register
    function, which is in turn required to call this register function for each of its modules, providing a name that
    identifies the module in the config file, and a creator function which will return an instance of the object when
    called. A module's creator function should be able to accept the parameters specified for this module in the config
    file.
    """
    plugin_creation_funcs[plugin_type] = creator_fn


def create(module_name: str, arguments: dict[str, Any]) -> Core:
    """Create an instance of a module previously registered with the factory.

    The module_name must be the same the one given when the factory.register function was called for the module.
    """
    try:
        creator_func = plugin_creation_funcs[module_name]
    except KeyError as exc:
        message = f"Unknown module: {module_name!r}"
        raise ValueError(message) from exc

    # TODO is this syntax still necessary if arguments is no longer optional?
    return creator_func(**(arguments or {}))
