from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Other[T]:
    """Represents data that does not conform to any of the other interface types provided by quark.

    If possible, use any of the other datatypes in your module's pre- and postprocessing methods. This will increase the
    probability that other modules can be used alongside it without needing any intermediate type-conversion modules.
    """

    data: T
