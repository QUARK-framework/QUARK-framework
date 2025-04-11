from __future__ import annotations
from dataclasses import dataclass

import numpy as np
import networkx as nx


@dataclass
class Graph:
    _g:nx.Graph

    @staticmethod
    def from_nx_graph(g: nx.Graph) -> Graph:
        return Graph(g)

    def as_nx_graph(self):
        return self._g

    @staticmethod
    def from_adjacency_matrix(matrix: np.ndarray) -> Graph:
        g = nx.Graph()
        # TODO
        return Graph(g)

    @staticmethod
    def postprocessed_type():
        return list[int]
