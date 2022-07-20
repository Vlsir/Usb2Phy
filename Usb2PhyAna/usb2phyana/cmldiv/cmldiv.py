"""
# CML Clock Divider 
"""

# Hdl & PDK Imports
import hdl21 as h
import s130
from s130 import MosParams

# Local Imports
from ..diff import Diff, inverse
from ..cmlparams import CmlParams

NmosLvt = s130.modules.nmos_lvt
Cap = h.primitives.Cap
Res = h.primitives.Res

# Define a few reused device-parameter combos
Nswitch = NmosLvt(MosParams(m=10))
Nbias = NmosLvt(MosParams(w=1, l=1, m=100))


@h.generator
def CmlLatch(p: CmlParams) -> h.Module:
    """# CML Latch
    Transparent when clock is (differentially) high."""

    @h.module
    class CmlLatch:
        # IO Interface
        VDD, VSS = h.Ports(2)
        ## Differential Clock & Data IO
        clk = Diff(port=True, role=Diff.Roles.SINK)
        d = Diff(port=True, role=Diff.Roles.SINK)
        q = Diff(port=True, role=Diff.Roles.SOURCE)
        ## Gate Bias for Current Sources
        bias = h.Input()

        # Internal Implementation

        ## Load Resistors
        rlp = Res(Res.Params(r=p.rl))(p=q.p, n=VDD)
        rln = Res(Res.Params(r=p.rl))(p=q.n, n=VDD)
        ## Load Caps
        clp = Cap(Cap.Params(c=p.cl))(p=q.p, n=VDD)
        cln = Cap(Cap.Params(c=p.cl))(p=q.n, n=VDD)
        ## Current Source
        ni = Nbias(g=bias, s=VSS, b=VSS)
        ## Clock Steering Pair
        ncp = Nswitch(s=ni.d, g=clk.p, b=VSS)
        ncn = Nswitch(s=ni.d, g=clk.n, b=VSS)
        ## Data Input Pair
        ndp = Nswitch(s=ncp.d, g=d.p, d=q.n, b=VSS)
        ndn = Nswitch(s=ncp.d, g=d.n, d=q.p, b=VSS)
        ## Cross-Coupled Feedback Pair
        nxp = Nswitch(s=ncn.d, g=q.p, d=q.n, b=VSS)
        nxn = Nswitch(s=ncn.d, g=q.n, d=q.p, b=VSS)

    return CmlLatch


@h.generator
def CmlDiv(p: CmlParams) -> h.Module:
    """# CML Clock Divider"""

    @h.module
    class CmlDiv:
        # IO Interface
        VDD, VSS = h.Ports(2)

        ## Primary IOs: Clock Input, I&Q Outputs
        clk = Diff(port=True, role=Diff.Roles.SINK, desc="Clock Input")
        q = Diff(port=True, role=Diff.Roles.SOURCE, desc="Quadrature Output")
        i = Diff(port=True, role=Diff.Roles.SOURCE, desc="In-Phase Output")

        ## Bias input and gate
        ibias = h.Input(desc="Current Bias Input")

        # Internal Implementation
        ## Current-Bias Transistor
        nb = Nbias(g=ibias, d=ibias, s=VSS, b=VSS)
        ## Input / Quadrature-Phase Generator Latch
        lq = CmlLatch(p)(
            clk=inverse(clk),  # Negate Clock Polarity
            d=inverse(i),  # And negate feedback of in-phase output
            q=q,  # Generates quadrature output
            bias=ibias,
            VDD=VDD,
            VSS=VSS,
        )
        ## Output / In-Phase Generator Latch
        li = CmlLatch(p)(
            clk=clk,  # Positive Clock Polarity
            d=q,
            q=i,  # Generates in-phase output
            bias=ibias,
            VDD=VDD,
            VSS=VSS,
        )

    return CmlDiv
