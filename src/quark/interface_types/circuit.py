from __future__ import annotations

from dataclasses import dataclass

from quark.interface_types.quantum_result import SampleDistribution


@dataclass
class Circuit:
    """A class for representing a quantum circuit."""

    _qasm_string: str

    def __post_init__(self):
        self._qasm_version: str | None = None

    def as_qasm_string(self) -> str:
        """Convert the circuit to an OpenQASM string."""
        return self._qasm_string

    @property
    def qasm_version(self) -> str:
        """Return the QASM version as String in the format M.m or None if not specified in the qasm."""
        if self._qasm_version is None:
            self._qasm_version = self._read_qasm_version()
        # self._qasm_version == None is used to indicate that the version has not been read yet. If no version is
        # specified in the qasm string self._qasm_version will be set to the empty string. The public property
        # qasm_version however will be None in this case.
        return None if not self._qasm_version else self._qasm_version

    def _read_qasm_version(self) -> str | None:
        # see https://openqasm.com/language/comments.html#version-string
        in_comment = False
        for line in self._qasm_string.split("\n"):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            if line.startswith("/*"):
                in_comment = True
            if in_comment and line.endswith("*/"):
                in_comment = False
                continue
            if not in_comment:
                # first_non_comment_line
                if line.startswith("OPENQASM"):
                    version = line.split()[1]
                    return version[:-1] # split off ";"
                else:
                    return ""


    @classmethod
    def from_qasm_string(cls, qasm_string: str) -> Circuit:
        """Create a Circuit instance from an OpenQASM string."""
        return cls(qasm_string)

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

__all__ = [
    "Circuit",
    "SampleDistribution",
]
