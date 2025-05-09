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
        v = Graph()
        v._g = g
        return v

    def as_nx_graph(self) -> nx.Graph:
        return self._g

    @staticmethod
    def from_adjacency_matrix(matrix: np.ndarray) -> Graph:
        raise NotImplementedError

    def as_adjacency_matrix(self) -> np.ndarray:
        raise NotImplementedError
