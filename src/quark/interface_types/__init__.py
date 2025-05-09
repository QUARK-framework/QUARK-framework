from quark.interface_types.graph import Graph
from quark.interface_types.ising import Ising
from quark.interface_types.other import Other
from quark.interface_types.qubo import Qubo

InterfaceType = Graph | Ising | Other | Qubo | None
