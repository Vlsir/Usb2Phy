"""
# High-Speed RX Pre-Amp
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21.prefix import m, K
from hdl21.primitives import R 

import s130
from s130 import IoMosParams 

# Local Imports
from ...diff import Diff


PmosIo = s130.modules.pmos_v5
Psf = PmosIo(IoMosParams(w=500 * m, l=500 * m, m=50))
Pbias = PmosIo(IoMosParams(w=10, l=10, m=50))


@h.module
class PreAmp:
    """ # RX Pre-Amp """

    # IO
    VDD33, VSS = h.Ports(2)
    inp = Diff(port=True, role=Diff.Roles.SINK)
    out = Diff(port=True, role=Diff.Roles.SOURCE)
    ibias = h.Input()

    # Internal Implementation 
    ## Bias Network 
    biasd = Pbias(g=ibias, d=ibias, s=VDD33, b=VDD33)
    biast = 2 * Pbias(g=ibias, s=VDD33, b=VDD33)
    ## Input Pair
    pinp = Psf(g=inp.p, d=out.n, s=biast.d, b=VDD33)
    pinn = Psf(g=inp.n, d=out.p, s=biast.d, b=VDD33)
    ## Load Resistors 
    rlp = R(R.Params(r=5 * K))(p=out.p, n=VSS)
    rln = R(R.Params(r=5 * K))(p=out.n, n=VSS)


@h.module
class _SourceFollowers:
    """ # RX Pre-Amp 
    Source Follower Edition """

    # IO
    VDD33, VSS = h.Ports(2)
    inp = Diff(port=True, role=Diff.Roles.SINK)
    out = Diff(port=True, role=Diff.Roles.SOURCE)
    ibias = h.Input()

    # Internal Implementation 
    ## Source Followers 
    sfp = Psf(d=VSS, g=inp.p, s=out.n, b=VDD33)
    sfn = Psf(d=VSS, g=inp.n, s=out.p, b=VDD33)
    ## Bias Network 
    biasp = Pbias(g=ibias, d=out.p, s=VDD33, b=VDD33)
    biasn = Pbias(g=ibias, d=out.n, s=VDD33, b=VDD33)
    biasd = Pbias(g=ibias, d=ibias, s=VDD33, b=VDD33)
