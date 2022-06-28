"""
# CML Phase Interpolator 
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21.prefix import m, p, n, K, f, µ
from hdl21.primitives import Vpulse, Vdc, Idc
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
from ...cml import CmlParams
from .encoder import PiEncoder


@h.paramclass
class PiParams:
    """ Phase Interpolator Parameters """

    nbits = h.Param(dtype=int, default=5, desc="Resolution, or width of select-input.")


@h.generator
def IdacTherm(p: CmlParams) -> h.Module:
    """ Current Dac, Thermometer Encoded """

    Unit = IdacUnit(p)

    @h.module
    class IdacTherm:
        # IO Interface
        VDD, VSS = h.Ports(2)
        itherm, qtherm = h.Inputs(2, width=8)
        iout, qout = h.Outputs(2)
        bias = h.Input()

        # Internal Implementation
        ## Primary current-switching units
        units = 7 * Unit(
            ep=itherm[1:], em=qtherm[1:], op=iout, om=qout, bias=bias, VDD=VDD, VSS=VSS
        )
        ## And add an always-on unit for each side
        uonp = Unit(ep=VDD, em=VSS, op=iout, om=qout, bias=bias, VDD=VDD, VSS=VSS)
        uonm = Unit(ep=VSS, em=VDD, op=iout, om=qout, bias=bias, VDD=VDD, VSS=VSS)

    return IdacTherm


@h.generator
def IdacUnit(_: CmlParams) -> h.Module:
    """ Current Dac Unit """

    @h.module
    class IdacUnit:
        # IO Interface
        VDD, VSS = h.Ports(2)
        ep, em = h.Inputs(2)
        op, om = h.Outputs(2)
        ## Gate Bias for Current Source
        bias = h.Input()
        nb = Nbias(g=bias, s=VSS, b=VSS)
        sw = 2 * Nswitch(g=h.Concat(ep, em), d=h.Concat(op, om), s=nb.d, b=VSS)

    return IdacUnit


@h.generator
def PhaseInterp(p: PiParams) -> h.Module:
    """ Phase Interpolator Generator """

    params = CmlParams(rl=4 * K, cl=25 * f, ib=250 * µ)

    @h.module
    class PhaseInterp:
        # IO Interface
        VDD, VSS = h.Ports(2)
        ckq = QuadClock(role=QuadClock.Roles.SINK, port=True, desc="Quadrature input")
        sel = h.Input(width=p.nbits, desc="Selection input")
        out = Diff(port=True, role=Diff.Roles.SOURCE)

        # Internal Implementation
        # qmuxck, imuxck = h.Signals(2, width=1, desc="MSB-Selected I&Q Phases")
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
            qtherm=qtherm, itherm=itherm, iout=daci, qout=dacq, bias=ibias, VDD=VDD, VSS=VSS
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
