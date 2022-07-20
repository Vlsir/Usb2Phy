""" 
# Differential Bundle
"""

# Std-Lib Imports
from enum import Enum, auto

# Hdl & PDK Imports
import hdl21 as h


@h.bundle
class Diff:
    """Differential Bundle"""

    class Roles(Enum):
        SOURCE = auto()
        SINK = auto()

    p, n = h.Signals(2, src=Roles.SOURCE, dest=Roles.SINK)


def inverse(d: Diff) -> h.AnonymousBundle:
    """Create a Bundle with the same signals as `d`, but with `p` and `n` reversed."""
    return h.AnonymousBundle(p=d.n, n=d.p)
