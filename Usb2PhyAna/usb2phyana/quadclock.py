# Std-Lib Imports
from typing import Dict
from enum import Enum, auto

# Hdl & PDK Imports
import hdl21 as h


@h.bundle
class QuadClock:
    """ # Quadrature Clock Bundle 
    Includes four 90-degree-separated phases. """

    class Roles(Enum):
        # Clock roles: source or sink
        SOURCE = auto()
        SINK = auto()

    # The four quadrature phases, all driven by SOURCE and consumed by SINK.
    ck0, ck90, ck180, ck270 = h.Signals(4, src=Roles.SOURCE, dest=Roles.SINK)
