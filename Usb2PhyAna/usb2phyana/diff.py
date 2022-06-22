# Std-Lib Imports
from typing import Dict
from enum import Enum, auto

# Hdl & PDK Imports
import hdl21 as h


@h.bundle
class Diff:
    """ Differential Bundle """

    class Roles(Enum):
        SOURCE = auto()
        SINK = auto()

    p, n = h.Signals(2, src=Roles.SOURCE, dest=Roles.SINK)
