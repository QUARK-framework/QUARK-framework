from __future__ import annotations
from dataclasses import dataclass

@dataclass
class SampleDistribution:
    """A class for representing a quantum sample distribution."""
    _samples: list[tuple[str, float]]

    def as_list(self) -> list[tuple[str, float]]:
        """Convert the sample distribution to a list of tuples."""
        return self._samples

    @classmethod
    def from_list(cls, samples: list[tuple[str, float]]) -> SampleDistribution:
        """Create a SampleDistribution instance from a list of tuples."""
        distribution = cls(samples)
        return distribution
    
    @classmethod
    def from_statevector(cls, statevector: list[complex], n_bits: int, n_shots: int = 1.0) -> SampleDistribution:
        """Create a SampleDistribution instance from a statevector."""
        samples = [(bin(state_int)[2:].zfill(n_bits), abs(amplitude)**2 * n_shots) for state_int, amplitude in enumerate(statevector)]
        distribution = cls(samples)
        return distribution
    
    
    
# @dataclass
# class ExpectationValue:
#     """A class for representing an expectation value of an observable."""
#     value: float
#     variance: float | None = None
