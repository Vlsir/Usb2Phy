"""
# CML Clock Divider 
"""

# Hdl & PDK Imports
import hdl21 as h
import s130
from s130 import MosParams

# Local Imports
from ..diff import Diff


NmosLvt = s130.modules.nmos_lvt
Cap = h.primitives.Cap
Res = h.primitives.Res

# Define a few reused device-parameter combos
Nswitch = NmosLvt(MosParams(m=10))
Nbias = NmosLvt(MosParams(w=1, l=1, m=100))


@h.paramclass
class CmlParams:
    """ CML Parameters """

    rl = h.Param(dtype=h.Prefixed, desc="Load Res Value (Ohms)")
    cl = h.Param(dtype=h.Prefixed, desc="Load Cap Value (F)")
    ib = h.Param(dtype=h.Prefixed, desc="Bias Current Value (A)")


@h.generator
def CmlBuf(p: CmlParams) -> h.Module:
    """ # CML Buffer """

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


@h.generator
def CmlLatch(p: CmlParams) -> h.Module:
    """ # CML Latch 
    Transparent when clock is (differentially) high. """

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
    """ # CML Clock Divider """

    @h.module
    class CmlDiv:
        # IO Interface
        VDD, VSS = h.Ports(2)

        # clk = Diff(port=True, role=Diff.Roles.SINK, desc="Clock Input")
        # q = Diff(port=True, role=Diff.Roles.SOURCE, desc="Quadrature Output")
        # i = Diff(port=True, role=Diff.Roles.SOURCE, desc="In-Phase Output")
        ## Sadly gotta use this scalar stuff for now!
        ckp, ckn = h.Inputs(2, desc="Clock Input")
        qp, qn = h.Outputs(2, desc="Quadrature Output")
        ip, in_ = h.Outputs(2, desc="In-Phase Output")
        ## Bias input and gate
        ibias = h.Input(desc="Current Bias Input")

        # Internal Implementation
        ## Current-Bias Transistor
        nb = Nbias(g=ibias, d=ibias, s=VSS, b=VSS)
        ## Input / Quadrature-Phase Generator Latch
        lq = CmlLatch(p)(
            clk=h.AnonymousBundle(p=ckn, n=ckp),  # Negate Clock Polarity
            d=h.AnonymousBundle(p=in_, n=ip),  # And negate feedback of in-phase output
            q=h.AnonymousBundle(p=qp, n=qn),  # Generates quadrature output
            bias=ibias,
            VDD=VDD,
            VSS=VSS,
        )
        ## Output / In-Phase Generator Latch
        li = CmlLatch(p)(
            clk=h.AnonymousBundle(p=ckp, n=ckn),  # Positive Clock Polarity
            d=h.AnonymousBundle(p=qp, n=qn),
            q=h.AnonymousBundle(p=ip, n=in_),  # Generates in-phase output
            bias=ibias,
            VDD=VDD,
            VSS=VSS,
        )

    return CmlDiv
