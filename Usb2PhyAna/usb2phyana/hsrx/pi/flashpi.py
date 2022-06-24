"""
# Phase Interpolator 
"""
# Hdl & PDK Imports
import hdl21 as h
import s130
from s130 import MosParams

nmos = s130.modules.nmos
pmos = s130.modules.pmos

# Local Imports
from ...quadclock import QuadClock
from ...encoders import OneHotEncoder
from ...triinv import TriInv


@h.paramclass
class WeightInvParams:
    weight = h.Param(dtype=int, desc="Weight")


@h.generator
def WeightInv(p: WeightInvParams) -> h.Module:

    m = h.Module()
    m.VDD, m.VSS = h.Ports(2)
    m.i = h.Input()
    m.z = h.Output()
    m.n = nmos(MosParams(w=1, m=p.weight))(d=m.z, g=m.i, s=m.VSS, b=m.VSS)
    m.p = pmos(MosParams(w=2, m=p.weight))(d=m.z, g=m.i, s=m.VDD, b=m.VDD)

    return m


@h.paramclass
class PhaseWeighterParams:
    wta = h.Param(dtype=int, desc="Weight of Input A")
    wtb = h.Param(dtype=int, desc="Weight of Input B")


@h.generator
def PhaseWeighter(p: PhaseWeighterParams) -> h.Module:
    """ # Phase-Weighter
    Drives a single output with two out-of-phase inputs `a` and `b`, 
    with weights dictates by params `wta` and `wtb`. """

    @h.module
    class PhaseWeighter:
        # IO Ports
        VDD, VSS = h.Ports(2)
        a, b = h.Inputs(2)
        out = h.Output()
        mix = h.Signal(desc="Internal phase-mixing node")

    # Give it a shorthand name for these manipulations
    P = PhaseWeighter

    if p.wta > 0:  # a-input inverter
        P.inva = WeightInv(WeightInvParams(weight=p.wta))(
            i=P.a, z=P.mix, VDD=P.VDD, VSS=P.VSS
        )
    if p.wtb > 0:  # b-input inverter
        P.invb = WeightInv(WeightInvParams(weight=p.wtb))(
            i=P.b, z=P.mix, VDD=P.VDD, VSS=P.VSS
        )

    # Output inverter, with the combined size of the two inputs
    P.invo = WeightInv(WeightInvParams(weight=1))(
        i=P.mix, z=P.out, VDD=P.VDD, VSS=P.VSS
    )

    return PhaseWeighter


@h.paramclass
class PiParams:
    """ Phase Interpolator Parameters """

    nbits = h.Param(dtype=int, default=5, desc="Resolution, or width of select-input.")


@h.generator
def PhaseGenerator(p: PiParams) -> h.Module:
    """ # Phase Generator (Generator) (Get it?) 
    
    Takes a primary input `QuadClock` and interpolates to produce 
    an array of equally-spaced output phases. """

    PhaseGen = h.Module()
    VDD, VSS = PhaseGen.VDD, PhaseGen.VSS = h.Ports(2)
    ckq = PhaseGen.ckq = QuadClock(
        role=QuadClock.Roles.SINK, port=True, desc="Quadrature input"
    )
    phases = PhaseGen.phases = h.Output(
        width=2 ** p.nbits, desc="Array of equally-spaced phases"
    )

    if p.nbits != 5:
        msg = f"Yeah we know that's a parameter, but this is actually hard-coded to 5 bits for now"
        raise ValueError(msg)

    # Generate a set of PhaseWeighters and output phases for each pair of quadrature inputs
    for wtb in range(8):
        p = PhaseWeighterParams(wta=8 - wtb, wtb=wtb)
        index = wtb
        PhaseGen.add(
            name=f"weight{index}",
            val=PhaseWeighter(p)(
                a=ckq.ck0, b=ckq.ck90, out=phases[index], VDD=VDD, VSS=VSS
            ),
        )
    for wtb in range(8):
        p = PhaseWeighterParams(wta=8 - wtb, wtb=wtb)
        index = 8 + wtb
        PhaseGen.add(
            name=f"weight{index}",
            val=PhaseWeighter(p)(
                a=ckq.ck90, b=ckq.ck180, out=phases[index], VDD=VDD, VSS=VSS
            ),
        )
    for wtb in range(8):
        p = PhaseWeighterParams(wta=8 - wtb, wtb=wtb)
        index = 16 + wtb
        PhaseGen.add(
            name=f"weight{index}",
            val=PhaseWeighter(p)(
                a=ckq.ck180, b=ckq.ck270, out=phases[index], VDD=VDD, VSS=VSS
            ),
        )
    for wtb in range(8):
        p = PhaseWeighterParams(wta=8 - wtb, wtb=wtb)
        index = 24 + wtb
        PhaseGen.add(
            name=f"weight{index}",
            val=PhaseWeighter(p)(
                a=ckq.ck270, b=ckq.ck0, out=phases[index], VDD=VDD, VSS=VSS
            ),
        )

    return PhaseGen


@h.generator
def PhaseSelector(p: PiParams) -> h.Module:
    """ # Phase Selector Mux """

    @h.module
    class PhaseSelector:
        # IO Interface
        VDD, VSS = h.Ports(2)
        phases = h.Input(width=2 ** p.nbits, desc="Array of equally-spaced phases")
        sel = h.Input(width=p.nbits, desc="Selection input")
        out = h.Output(width=1, desc="Clock output")

        # Internal Contents
        encoder = OneHotEncoder(width=5)(bin=sel, en=VDD, VDD=VDD, VSS=VSS)
        invs = 32 * TriInv(width=4)(i=phases, en=encoder.out, z=out, VDD=VDD, VSS=VSS)

    return PhaseSelector


@h.generator
def PhaseInterp(p: PiParams) -> h.Module:
    """ Phase Interpolator Generator """

    @h.module
    class PhaseInterp:
        # IO Interface
        VDD, VSS = h.Ports(2)
        ckq = QuadClock(role=QuadClock.Roles.SINK, port=True, desc="Quadrature input")
        sel = h.Input(width=p.nbits, desc="Selection input")
        out = h.Output(width=1, desc="Clock output")

        # Internal Signals
        phases = h.Signal(width=2 ** p.nbits, desc="Array of equally-spaced phases")

        # Instantiate the phase-generator and phase-selector
        phgen = PhaseGenerator(p)(ckq=ckq, phases=phases, VDD=VDD, VSS=VSS)
        phsel = PhaseSelector(p)(phases=phases, sel=sel, out=out, VDD=VDD, VSS=VSS)

    return PhaseInterp
