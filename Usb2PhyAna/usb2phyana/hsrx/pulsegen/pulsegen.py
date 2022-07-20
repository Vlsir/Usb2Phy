"""
# CML Pulse Generator
"""

# Hdl & PDK Imports
import hdl21 as h
import s130
from s130 import MosParams

# Local Imports
from ...diff import Diff, inverse
from ...cmlparams import CmlParams


NmosLvt = s130.modules.nmos_lvt
Cap = h.primitives.Cap
Res = h.primitives.Res

# Define a few reused device-parameter combos
Nswitch = NmosLvt(MosParams(m=10))
Nbias = NmosLvt(MosParams(w=1, l=1, m=100))


@h.generator
def CmlDelayBuf(p: CmlParams) -> h.Module:
    """# CML Delay Buffer"""

    @h.module
    class CmlDelayBuf:
        # IO Interface
        VDD, VSS = h.Ports(2)

        ## Differential Input & Output
        i = Diff(port=True, role=Diff.Roles.SINK)
        o = Diff(port=True, role=Diff.Roles.SOURCE)

        ## Gate Bias for Current Sources
        bias = h.Input()

        # Internal Implementation

        ## Load Resistors
        rlp = Res(Res.Params(r=p.rl))(p=o.p, n=VDD)
        rln = Res(Res.Params(r=p.rl))(p=o.n, n=VDD)
        ## Load Caps
        clp = Cap(Cap.Params(c=p.cl))(p=o.p, n=VDD)
        cln = Cap(Cap.Params(c=p.cl))(p=o.n, n=VDD)
        ## Current Bias
        ni = Nbias(g=bias, s=VSS, b=VSS)
        ## Input Pair
        ndp = Nswitch(s=ni.d, g=i.p, d=o.n, b=VSS)
        ndn = Nswitch(s=ni.d, g=i.n, d=o.p, b=VSS)

    return CmlDelayBuf


@h.generator
def CmlXor(p: CmlParams) -> h.Module:
    """# CML XOR"""

    @h.module
    class CmlXor:
        # IO Interface
        VDD, VSS = h.Ports(2)
        ## Differential IO
        a = Diff(port=True, role=Diff.Roles.SINK)
        b = Diff(port=True, role=Diff.Roles.SINK)
        x = Diff(port=True, role=Diff.Roles.SOURCE)
        ## Bias Current
        bias = h.Input()

        # Internal Implementation
        biasdrain = h.Signal()
        ## Bias Current
        ni = Nbias(g=bias, d=biasdrain, s=VSS, b=VSS)

        ## Intra-Quad Nets
        intra = h.Signal(width=4)
        ## Bottom Quad
        napb = Nswitch(s=biasdrain, g=a.p, d=intra[0], b=VSS)
        nanb = Nswitch(s=biasdrain, g=a.n, d=intra[1], b=VSS)
        nbpb = Nswitch(s=biasdrain, g=b.p, d=intra[2], b=VSS)
        nbnb = Nswitch(s=biasdrain, g=b.n, d=intra[3], b=VSS)
        ## Top Quad
        nbpt = Nswitch(s=intra[0], g=b.p, d=x.p, b=VSS)
        nbnt = Nswitch(s=intra[1], g=b.n, d=x.p, b=VSS)
        nant = Nswitch(s=intra[2], g=a.n, d=x.n, b=VSS)
        napt = Nswitch(s=intra[3], g=a.p, d=x.n, b=VSS)

        ## Load Resistors
        rlp = Res(Res.Params(r=p.rl))(p=x.p, n=VDD)
        rln = Res(Res.Params(r=p.rl))(p=x.n, n=VDD)
        ## Load Caps
        ## FIXME: none intentionally added, at least not the same amount as the other CML stages
        # clp = Cap(Cap.Params(c=p.cl))(p=x.p, n=VDD)
        # cln = Cap(Cap.Params(c=p.cl))(p=x.n, n=VDD)

    return CmlXor


@h.generator
def CmlPulseGen(p: CmlParams) -> h.Module:
    """# CML Pulse Generator"""

    @h.module
    class CmlPulseGen:
        # IO Interface
        VDD, VSS = h.Ports(2)

        ## Primary Differential IOs
        inp = Diff(port=True, role=Diff.Roles.SINK, desc="Primary Input")
        out = Diff(port=True, role=Diff.Roles.SOURCE, desc="Pulse Output")
        ## Bias input and gate
        ibias = h.Input(desc="Current Bias Input")

        # Internal Implementation
        ## Current-Bias Transistor
        nb = Nbias(g=ibias, d=ibias, s=VSS, b=VSS)
        ## Delay Buffer
        dly = Diff(desc="Delayed Input")
        buf = CmlDelayBuf(p)(
            i=inp,
            o=dly,
            bias=ibias,
            VDD=VDD,
            VSS=VSS,
        )
        ## Delay Buffer #2
        dly2 = Diff(desc="Delayed Input #2")
        buf2 = CmlDelayBuf(p)(
            i=dly,
            o=dly2,
            bias=ibias,
            VDD=VDD,
            VSS=VSS,
        )
        ## Xor
        xor = CmlXor(p)(
            a=inp,
            b=dly2,
            x=out,
            bias=ibias,
            VDD=VDD,
            VSS=VSS,
        )

    return CmlPulseGen
