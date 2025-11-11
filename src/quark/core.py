# ruff: noqa: ANN401

"""The Core abstract base class.

Each module must inherit from the Core class and implement its abstract functions. Core also provides some non-abstract
functions which contain default implementations and can be overridden by a module, if desired.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from quark.interface_types import InterfaceType


@dataclass(frozen=True)
class Sleep:
    """Special return value for preprocess and postprocess methods.

    Can be returned by a module to signal that a waiting period is necessary. Once all other pipelines are finished,
    interrupted, or sleeping, execution will be paused and the current program state will be stored. Quark can be
    executed again at a later time to continue execution. Depending on whether the sleep object was returned from the
    pre- or postprocessing method, the respective method will be called again, this time with the data stored in the
    stored_data field of the Sleep object.
    """

    stored_data: InterfaceType


@dataclass(frozen=True)
class Backtrack:
    """TODO: Not implemented yet."""

    data: InterfaceType


@dataclass(frozen=True)
class Data:
    """Standard return value for preprocess and postprocess methods."""

    data: InterfaceType


@dataclass(frozen=True)
class Failed:
    """Indicates that the module has failed processing."""

    reason: str


Result = Sleep | Backtrack | Data | Failed


class Core(ABC):
    """Core module interface, implemented by all other modules that are part of a benchmarking pipeline."""

    @abstractmethod
    def preprocess(self, data: Any) -> Result:
        """Essential method for the benchmarking process.

        This is always executed before traversing down to the next module, passing the data returned by this function.

        :param data: Data for the module, comes from the parent module if that exists
        :return: The processed data or an Interruption enum
        """
        raise NotImplementedError

    @abstractmethod
    def postprocess(self, data: Any) -> Result:
        """Essential method for the benchmarking process.

        Is always executed after the submodule is finished. The data by this method is passed up to the parent module.

        :param data: Input data comes from the submodule if that exists
        :return: The processed data or an Interruption enum
        """
        raise NotImplementedError

    def get_metrics(self) -> dict:
        """Return all relevant, human-readable metrics of the module to be written to a json file for later analysis.

        Is called right after the postprocess method.
        The module's config parameters are written to a file regardless of what is returned here.
        Best practice is to only include human-readable data that gives insights into the module's performance or
        results.

        :return: Dictionary containing all relevant metrics
        """
        return {}

    def get_unique_name(self) -> str | None:
        """Return a string representation of the module to be used in the file names for benchmark results.

        The string should be human-readable, not too long, and be unique in regard to the parameters given to the
        module.
        Two different instances of the same module should return different strings if they were given different
        parameters.

        :return: An identifying string of the module instance. If None, a name is chosen automatically.
        """
        return None

    # def handle_backtrack(self, data: Any) -> Result:
    #     """Override this method if you want to handle backtracking from a child node."""
    #     raise notImplementedError("One of the child nodes tried to backtrack,
    #     but the parent module does not override handle_backtrack")
