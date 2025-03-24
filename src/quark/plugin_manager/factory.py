from typing import Any, Callable

from quark.protocols import Core

plugin_creation_funcs: dict[str, Callable[..., Core]] = {}

def register(plugin_type: str, creator_fn: Callable[..., Core]) -> None:
    plugin_creation_funcs[plugin_type] = creator_fn

def unregister(plugin_type: str) -> None:
    plugin_creation_funcs.pop(plugin_type, None)

def create(plugin_type: str, arguments: dict[str, Any]) -> Core:
    try:
        creator_func = plugin_creation_funcs[plugin_type]
    except KeyError as exc:
        raise ValueError(f"Unknown plugin type {plugin_type!r}") from exc

    return creator_func(**(arguments or {}))
