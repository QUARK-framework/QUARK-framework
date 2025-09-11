from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

# Check back with RUFF T0002: https://docs.astral.sh/ruff/rules/typing-only-third-party-import/
if TYPE_CHECKING:
    import numpy as np


class Graph:
    """A class for representing a graph problem."""

    _g: nx.Graph

    @staticmethod
    def from_nx_graph(g: nx.Graph) -> Graph:
        """Create a Graph object from a networkx.Graph object."""
        v = Graph()
        v._g = g
        return v

    def as_nx_graph(self) -> nx.Graph:
        """Create a networkx.Graph object from this Graph object."""
        return self._g

    @staticmethod
    def from_adjacency_matrix(matrix: np.ndarray) -> Graph:
        """Create a Graph object from an adjacency matrix, given as a numpy.ndarray."""
        v = Graph()
        v._g = nx.from_numpy_array(matrix)
        return v

    def as_adjacency_matrix(self) -> np.ndarray:
        """Create an adjacency matrix as a numpy.ndarray from this Graph object."""
        return nx.to_numpy_array(self._g)
