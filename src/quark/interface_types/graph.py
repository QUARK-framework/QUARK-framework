from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import networkx as nx
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
        raise NotImplementedError

    def as_adjacency_matrix(self) -> np.ndarray:
        """Create an adjacency matrix as a numpy.ndarray from this Graph object."""
        raise NotImplementedError
