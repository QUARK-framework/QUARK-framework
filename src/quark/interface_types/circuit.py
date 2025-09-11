from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Circuit:
    """A class for representing a quantum circuit."""
    _qasm_string: str

    def as_qasm_string(self) -> str:
        """Convert the circuit to an OpenQASM string."""
        return self._qasm_string

    @classmethod
    def from_qasm_string(cls, qasm_string: str) -> Circuit:
        """Create a Circuit instance from an OpenQASM string."""
        circuit = cls()
        circuit._qasm_string = qasm_string
        return circuit
    
    # @property
    # def qir(self) -> str:
    #     """Convert the QASM string to a QIR string."""
    #     # This is a placeholder for the actual conversion logic
    #     return f"QIR representation of {self._qasm_string}"
    #
    # @property
    # def qiskit_quantum_circuit(self) -> str:
    #     """Convert the QASM string to a Qiskit circuit."""
    #     # This is a placeholder for the actual conversion logic
    #     return f"Qiskit representation of {self._qasm_string}"
    
    
