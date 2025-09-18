from __future__ import annotations
from dataclasses import dataclass
import math

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
    def from_statevector(cls, statevector: list[complex]) -> SampleDistribution:
        """Create a SampleDistribution instance from a statevector."""
        n_bits = int(math.ceil(math.log2(len(statevector))))  # Number of bits needed to represent the states
        samples = [(bin(state_int)[2:].zfill(n_bits), abs(amplitude)**2 )
                   for state_int, amplitude in enumerate(statevector) if abs(amplitude) > 0]
        distribution = cls(samples)
        return distribution
    
    
    
# @dataclass
# class ExpectationValue:
#     """A class for representing an expectation value of an observable."""
#     value: float
#     variance: float | None = None
