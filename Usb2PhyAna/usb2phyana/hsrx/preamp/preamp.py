"""
# High-Speed RX Pre-Amp
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21.prefix import m, K
from hdl21.primitives import R
from hdl21 import Diff, Pair

# PDK Imports
import s130
from s130 import IoMosParams

PmosIo = s130.modules.pmos_v5
Psf = PmosIo(IoMosParams(w=500 * m, l=500 * m, m=50))
Pbias = PmosIo(IoMosParams(w=10, l=10, m=50))


@h.generator
def PreAmp(_: h.HasNoParams) -> h.Module:
    """# RX Pre-Amp"""

    @h.module
    class PreAmp:
        # IO
        VDD33, VSS = h.Ports(2)
        inp = Diff(port=True, role=Diff.Roles.SINK)
        out = Diff(port=True, role=Diff.Roles.SOURCE)
        pbias = h.Input()

        # Internal Implementation
        ## Bias Network
        biasd = Pbias(g=pbias, d=pbias, s=VDD33, b=VDD33)
        biast = 2 * Pbias(g=pbias, s=VDD33, b=VDD33)
        ## Input Pair
        pin = Pair(Psf)(g=inp, d=out, s=biast.d, b=VDD33)
        ## Load Resistors
        rl = h.Pair(R(r=5 * K))(p=out, n=VSS)

    return PreAmp
