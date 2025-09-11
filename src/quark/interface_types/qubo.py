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
        # Look for largest qubit index, assuming all single qubits (on the diagonal) have a value != 0 in the QUBO
        n = max(int(key.split(",")[0][1:]) for key in qubo_dict) + 1  # +1 for zero-indexing
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

    def as_dnx_qubo(self) -> dict:
        """Return the QUBO as a dictionary suitable for D-Wave NetworkX."""
        qubo_matrix = self._factors
        n = int(np.sqrt(len(qubo_matrix)))
        q = {}
        for i in range(n * n):
            for j in range(n * n):
                if qubo_matrix[i, j] != 0:
                    i_tuple = (i // n, i % n)
                    j_tuple = (j // n, j % n)
                    q[(i_tuple, j_tuple)] = qubo_matrix[i, j]
        return q

    @classmethod
    def from_dnx_qubo(cls, qubo: dict, n: int) -> Qubo:
        """Create a QUBO from a D-Wave NetworkX dictionary."""
        qubo_matrix = np.zeros((n * n, n * n))
        # Fill the QUBO matrix from the dictionary
        for (i, j), value in qubo.items():
            # Convert the tuple (i, j) to a single index in the QUBO matrix
            qubo_matrix[i[0] * n + i[1]][j[0] * n + j[1]] = value
        # Since the QUBO is symmetric, fill the symmetric part
        for i in range(n * n):
            for j in range(n * n):
                if qubo_matrix[i, j] != 0:
                    qubo_matrix[j, i] = qubo_matrix[i, j]
        return cls.from_matrix(qubo_matrix)
