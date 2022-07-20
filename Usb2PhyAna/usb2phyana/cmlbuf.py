"""
# CML Buffer
"""

# Hdl & PDK Imports
import hdl21 as h
import s130
from s130 import MosParams

# Local Imports
from .diff import Diff
from .cmlparams import CmlParams

NmosLvt = s130.modules.nmos_lvt
Cap = h.primitives.Cap
Res = h.primitives.Res

# Define a few reused device-parameter combos
Nswitch = NmosLvt(MosParams(m=10))
Nbias = NmosLvt(MosParams(w=1, l=1, m=100))


@h.generator
def CmlBuf(p: CmlParams) -> h.Module:
    """# CML Buffer"""

    @h.module
    class CmlBuf:
        # IO Interface
        VDD, VSS = h.Ports(2)

        ## Differential Input & Output
        i = Diff(port=True, role=Diff.Roles.SINK)
        o = Diff(port=True, role=Diff.Roles.SOURCE)

        ## Gate Bias for Current Sources
        ibias = h.Input()

        # Internal Implementation

        ## Load Resistors
        rlp = Res(Res.Params(r=p.rl))(p=o.p, n=VDD)
        rln = Res(Res.Params(r=p.rl))(p=o.n, n=VDD)
        ## Load Caps
        clp = Cap(Cap.Params(c=p.cl))(p=o.p, n=VDD)
        cln = Cap(Cap.Params(c=p.cl))(p=o.n, n=VDD)
        ## Current Mirror
        nd = Nbias(g=ibias, d=ibias, s=VSS, b=VSS)
        ni = Nbias(g=ibias, s=VSS, b=VSS)
        ## Input Pair
        ndp = Nswitch(s=ni.d, g=i.p, d=o.n, b=VSS)
        ndn = Nswitch(s=ni.d, g=i.n, d=o.p, b=VSS)

    return CmlBuf
