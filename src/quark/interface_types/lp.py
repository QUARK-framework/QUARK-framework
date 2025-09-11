from __future__ import annotations

from pathlib import Path


class LP:
    """A class for representing linear programs (LP) readable by common LP solvers."""

    _lp_string: str

    def as_str(self) -> str:
        """Return the LP from a string."""
        return self._lp_string

    @classmethod
    def from_str(cls, string: str) -> LP:
        """Create the interface type from an LP-string."""
        lp = cls()
        lp._lp_string = string

        return lp

    @classmethod
    def from_file(cls, file_path: str | Path) -> LP:
        """Create an LP from a file."""
        lp = cls()

        with Path(file_path).open("r") as file:
            lp._lp_string = file.read()

        return lp
