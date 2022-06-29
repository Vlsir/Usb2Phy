"""
# CML Phase Interpolator 
"""

# Std-Lib Imports 
from enum import Enum, auto

# Hdl & PDK Imports
import hdl21 as h
from hdl21.prefix import K, f, µ
from hdl21.primitives import Idc
import s130
from s130 import MosParams

NmosLvt = s130.modules.nmos_lvt
Cap = h.primitives.Cap
Res = h.primitives.Res

Nswitch = NmosLvt(MosParams(m=4))
Nbias = NmosLvt(MosParams(w=1, l=1, m=100))


# Local Imports
from ...quadclock import QuadClock
from ...diff import Diff
from ...logiccells import Inv
from ...cmlparams import CmlParams
from .encoder import PiEncoder


@h.paramclass
class PiParams:
    """ Phase Interpolator Parameters """

    nbits = h.Param(dtype=int, default=5, desc="Resolution, or width of select-input.")

@h.bundle 
class IqPair:
    """ 
    # I/Q Signal Pair 
    Pair of signals which represent in-phase and quadrature components of a complex signal.
    """

    class Roles(Enum):
        SOURCE = auto()
        SINK = auto()

    i, q = h.Signals(2, width=1, src=Roles.SOURCE, dest=Roles.SINK)


@h.generator
def IdacTherm(p: CmlParams) -> h.Module:
    """ Current Dac, Thermometer Encoded """

    Unit = IdacUnit(p)

    @h.module
    class IdacTherm:
        # IO Interface
        VDD, VSS = h.Ports(2)

        itherm, qtherm = h.Inputs(2, width=8, desc="Thermometer Encoded I/Q Codes")
        out = IqPair(port=True, role=IqPair.Roles.SOURCE)
        bias = h.Input()

        # Internal Implementation
        ## Primary current-switching units
        units = 7 * Unit(
            eni=itherm[1:], enq=qtherm[1:], out=out, bias=bias, VDD=VDD, VSS=VSS
        )
        ## And add an always-on unit for each side
        uoni = Unit(eni=VDD, enq=VSS, out=out, bias=bias, VDD=VDD, VSS=VSS)
        uonq = Unit(eni=VSS, enq=VDD, out=out, bias=bias, VDD=VDD, VSS=VSS)

    return IdacTherm


@h.generator
def IdacUnit(_: CmlParams) -> h.Module:
    """ Current Dac Unit """

    @h.module
    class IdacUnit:
        # IO Interface
        VDD, VSS = h.Ports(2)

        eni, enq = h.Inputs(2, desc="Enable I/Q Inputs")
        out = IqPair(port=True, role=IqPair.Roles.SOURCE)

        ## Gate Bias and Current Source
        bias = h.Input()
        nb = Nbias(g=bias, s=VSS, b=VSS)

        ## Differential Current-Switch 
        swi = Nswitch(g=eni, d=out.i, s=nb.d, b=VSS)
        swq = Nswitch(g=enq, d=out.q, s=nb.d, b=VSS)

    return IdacUnit


@h.generator
def PhaseInterp(p: PiParams) -> h.Module:
    """ Phase Interpolator Generator """

    params = CmlParams(rl=4 * K, cl=25 * f, ib=250 * µ)

    @h.module
    class PhaseInterp:
        # IO Interface
        VDD, VSS = h.Ports(2)
        
        ckq = QuadClock(role=QuadClock.Roles.SINK, port=True, desc="Quadrature clock input")
        out = Diff(port=True, role=Diff.Roles.SOURCE, desc="Output clock")
        sel = h.Input(width=p.nbits, desc="Selection input")

        # Internal Implementation
        qtherm, itherm = h.Signals(2, width=8)
        isel, iselb, qsel, qselb = h.Signals(4)
        encoder = PiEncoder(width=p.nbits)(
            bin=sel,
            qmuxsel=qsel,
            imuxsel=isel,
            qtherm=qtherm,
            itherm=itherm,
            en=VDD,
            VDD=VDD,
            VSS=VSS,
        )
        invqsel = Inv(i=qsel, z=qselb, VDD=VDD, VSS=VSS)
        invisel = Inv(i=isel, z=iselb, VDD=VDD, VSS=VSS)

        ## Current DAC
        ## FIXME: cheating! bias current being ideally generated internally, sue us
        ibias = h.Signal()
        ii = Idc(Idc.Params(dc=-1 * params.ib))(p=ibias, n=VSS)
        nb = Nbias(g=ibias, d=ibias, s=VSS, b=VSS)
        daci, dacq = h.Signals(2)
        idac = IdacTherm(params)(
            qtherm=qtherm, 
            itherm=itherm, 
            out=h.AnonymousBundle(i=daci, q=dacq),
            bias=ibias, VDD=VDD, VSS=VSS
        )

        ## The "MSB Mux": a set of four polarity-inverting switches
        ckpairsources = h.Signal(width=4)
        mux = 4 * NmosLvt(MosParams(m=40))(
            d=ckpairsources,
            g=h.Concat(isel, iselb, qsel, qselb),
            s=h.Concat(daci, daci, dacq, dacq),
            b=VSS,
        )

        ## Load Resistors
        rlp = Res(Res.Params(r=params.rl / 8))(p=out.p, n=VDD)
        rln = Res(Res.Params(r=params.rl / 8))(p=out.n, n=VDD)
        ## Load Caps
        clp = Cap(Cap.Params(c=params.cl))(p=out.p, n=VDD)
        cln = Cap(Cap.Params(c=params.cl))(p=out.n, n=VDD)

    Pi = PhaseInterp

    ## The real show: the quadrature-clock-driven diff pairs
    ## FIXME: concatenating those Bundle reference Signals!!
    d = [Pi.out.n, Pi.out.p, Pi.out.p, Pi.out.n]
    g = [Pi.ckq.ck0, Pi.ckq.ck180, Pi.ckq.ck0, Pi.ckq.ck180]
    s = 2 * [Pi.ckpairsources[0]] + 2 * [Pi.ckpairsources[1]]
    for idx in range(4):
        inst = Nswitch(d=d[idx], g=g[idx], s=s[idx], b=Pi.VSS,)
        Pi.add(name=f"ni{idx}", val=inst)

    g = [Pi.ckq.ck90, Pi.ckq.ck270, Pi.ckq.ck90, Pi.ckq.ck270]
    s = 2 * [Pi.ckpairsources[2]] + 2 * [Pi.ckpairsources[3]]
    for idx in range(4):
        inst = Nswitch(d=d[idx], g=g[idx], s=s[idx], b=Pi.VSS,)
        Pi.add(name=f"nq{idx}", val=inst)

    return PhaseInterp
