from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Qubo:
    """A class for representing a Quadratic Unconstrained Binary Optimization problem."""

    # Every entry represents a coefficient of the qubo matrix
    _q: dict

    def as_dict(self):
        return self._q

    @staticmethod
    def from_dict(q: dict) -> Qubo:
        return Qubo(q)

    # def as_matrix(self):
    #     pass

    # @staticmethod
    # def from_matrix(matrix: np.ndarray) -> Qubo:
    #     pass

    # def as_ising(self):
    #     pass

    # @staticmethod
    # def from_ising(ising: Ising) -> Qubo:
    #     pass
