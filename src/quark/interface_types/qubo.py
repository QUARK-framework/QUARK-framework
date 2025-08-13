from __future__ import annotations

import numpy as np


class Qubo:
    """A class for representing a quadratic unconstrained binary optimization (QUBO) problem."""

    _factors: np.ndarray

    def as_matrix(self) -> np.ndarray:
        """Return the QUBO as a matrix."""
        return self._factors

    @classmethod
    def from_matrix(cls, matrix: np.ndarray) -> Qubo:
        """Create a QUBO from a matrix."""
        qubo = cls()
        qubo._factors = matrix
        return qubo

    def as_dict(self) -> dict:
        """Return the QUBO as a dictionary."""
        qubo_dict = {}
        # Factors matrix is always quadratic
        n = self._factors.shape[0]
        for i in range(n):
            # Matrix is symmetric, so we only need to iterate over the upper triangle
            for j in range(i, n):
                if i == j:
                    qubo_dict[f"q{i}"] = self._factors[i, j]
                else:
                    qubo_dict[f"q{i},q{j}"] = self._factors[i, j]
        return qubo_dict

    @classmethod
    def from_dict(cls, qubo_dict: dict) -> Qubo:
        """Create a QUBO from a dictionary.

        The keys should be in the format 'q0', 'q1', ...,
        or 'q0,q1', 'q0,q2', ... for single qubits and pairs of qubits, respectively.
        """
        n_0 = max(int(key.split(",")[0][1:]) for key in qubo_dict)
        n_1 = max(int(key.split(",")[1][1:]) for key in qubo_dict)
        n = max(n_0, n_1) # +1 for zero-indexing
        matrix = np.zeros((n, n))
        for key, value in qubo_dict.items():
            if "," in key:
                i, j = key.split(",")
                i = int(i[1:])  # Skip the 'q' prefix
                j = int(j[1:])  # Skip the 'q' prefix
                matrix[i, j] = value
                matrix[j, i] = value  # Ensure symmetry
            else:
                i = int(key[1:])  # Skip the 'q' prefix
                matrix[i, i] = value
        return cls.from_matrix(matrix)
