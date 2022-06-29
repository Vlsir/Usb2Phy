"""
# Phase Interpolator 

CMOS edition, with I/Q MSB muxes and control paired with `pi.PiEncoder`. 
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21.prefix import f

Cap = h.primitives.Cap

# Local Imports
from ...diff import Diff
from ...quadclock import QuadClock
from .encoder import PiEncoder
from ...triinv import TriInv
from ...logiccells import Inv


@h.paramclass
class PiParams:
    """ Phase Interpolator Parameters """

    nbits = h.Param(dtype=int, default=5, desc="Resolution, or width of select-input.")


@h.generator
def FineInterp(_: PiParams) -> h.Module:
    """ # MSB Mux 
    Generates pair of outputs "early clock" and "late clock" `qck` and `ick` dictated by `sel`. """

    InterpTriInv = TriInv(width=1)

    @h.module
    class FineInterp:
        # IO Interface
        VDD, VSS = h.Ports(2)
        qck, ick = h.Inputs(2, width=1, desc="In-phase & quadrature clock inputs")
        qtherm, itherm = h.Inputs(2, width=8, desc="Thermometer encoded codes")
        out = h.Output(width=1, desc="Clock output")

        # Internal Implementation

        ## Main Event: the interpolation tristate inverters
        ### Note the always-on element is injected here, by replacing the always-off 8th element of each thermo-code with an element tied to VDD.
        outb = h.Signal()
        _qen = h.Concat(VDD, qtherm[1:])
        qinvs = 8 * InterpTriInv(i=qck, en=_qen, z=outb, VDD=VDD, VSS=VSS)
        _ien = h.Concat(VDD, itherm[1:])
        iinvs = 8 * InterpTriInv(i=ick, en=_ien, z=outb, VDD=VDD, VSS=VSS)

        ## Output Inverter
        oinv = InterpTriInv(i=outb, en=VDD, z=out, VDD=VDD, VSS=VSS)

        ## Load Caps
        clb = Cap(Cap.Params(c=50 * f))(p=outb, n=VSS)
        clo = Cap(Cap.Params(c=10 * f))(p=out, n=VSS)

    return FineInterp


@h.module
class Mux2to1:
    """ Two to One Tri-State Mux """

    # IO Interface
    VDD, VSS = h.Ports(2)
    if0, if1 = h.Inputs(2, width=1, desc="Data Inputs")
    sel = h.Input(width=1, desc="Select")
    out = h.Output(width=1, desc="Output")

    # Internal Implementation
    isel = Inv()(i=sel, VDD=VDD, VSS=VSS)
    ta = TriInv(width=1)(i=if1, z=out, en=sel, VDD=VDD, VSS=VSS)
    tb = TriInv(width=1)(i=if0, z=out, en=isel.z, VDD=VDD, VSS=VSS)


@h.generator
def PhaseInterp(p: PiParams) -> h.Module:
    """ Phase Interpolator Generator """

    @h.module
    class PhaseInterp:
        # IO Interface
        VDD, VSS = h.Ports(2)

        ckq = QuadClock(role=QuadClock.Roles.SINK, port=True, desc="Quadrature clock input")
        out = Diff(port=True, role=Diff.Roles.SOURCE, desc="Output clock")
        sel = h.Input(width=p.nbits, desc="Selection input")

        # Internal Implementation
        qmuxck, imuxck = h.Signals(2, width=1, desc="MSB-Selected I&Q Phases")
        encoder = PiEncoder(width=p.nbits)(bin=sel, en=VDD, VDD=VDD, VSS=VSS)

        ## MSB Selection Mux
        qmux = Mux2to1(
            if0=ckq.ck90, if1=ckq.ck270, sel=encoder.qmuxsel, out=qmuxck, VDD=VDD, VSS=VSS
        )
        imux = Mux2to1(
            if0=ckq.ck0, if1=ckq.ck180, sel=encoder.imuxsel, out=imuxck, VDD=VDD, VSS=VSS
        )

        ## LSB / Fine Interpolator
        ### FIXME: driving differential/ complementary output 
        fine = FineInterp(p)(
            qck=qmuxck,
            ick=imuxck,
            qtherm=encoder.qtherm,
            itherm=encoder.itherm,
            out=out.p,
            VDD=VDD,
            VSS=VSS,
        )

    return PhaseInterp
