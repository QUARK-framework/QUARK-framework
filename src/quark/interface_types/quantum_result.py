from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SampleDistribution:
    """A class for representing a quantum sample distribution."""

    _samples: list[tuple[str, float]]
    _nbshots: int

    def as_list(self) -> list[tuple[str, float]]:
        """Convert the sample distribution to a list of tuples."""
        return self._samples

    @property
    def nbshots(self) -> int:
        """Return the number of shots from which the sample distribution was obtained."""
        return self._nbshots

    @classmethod
    def from_list(cls, samples: list[tuple[str, float]], nbshots:int) -> SampleDistribution:
        """Create a SampleDistribution instance from a list of tuples.

        Each tuple contains the state as a String of "0" and "1" characters and the corresponding relative count or
        probability. If relative counts are given nbshots must be set to the number of shots from which the relative
        count is taken. If exact probabilities are given (e.g. from algebraic calculations) nbshots must be set to 0.
        """
        if not isinstance(nbshots, int) or not nbshots >= 0:
            msg = "nbshots must be a non-negative integer (0 indicates exact probabilities)."
            raise ValueError(msg)
        return cls(samples, nbshots)

# @dataclass
# class ExpectationValue:
#     """A class for representing an expectation value of an observable."""
#     value: float
#     variance: float | None = None
