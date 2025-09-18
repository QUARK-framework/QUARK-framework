from quark.interface_types.graph import Graph
from quark.interface_types.ising import Ising
from quark.interface_types.lp import LP
from quark.interface_types.other import Other
from quark.interface_types.qubo import Qubo
from quark.interface_types.circuit import Circuit
from quark.interface_types.quantum_result import SampleDistribution

InterfaceType = Graph | Ising | Other | Qubo | Circuit | LP | SampleDistribution | None
