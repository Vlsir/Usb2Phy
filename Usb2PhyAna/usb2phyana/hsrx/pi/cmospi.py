"""
# Phase Interpolator 
"""
# Hdl & PDK Imports
import hdl21 as h
from hdl21.prefix import f

Cap = h.primitives.Cap

# Local Imports
from ...diff import Diff
from ...quadclock import QuadClock
from ...encoders import OneHotEncoder, ThermoEncoder3to8
from ...triinv import TriInv
from ...logiccells import Inv


@h.paramclass
class PiParams:
    """Phase Interpolator Parameters"""

    nbits = h.Param(dtype=int, default=5, desc="Resolution, or width of select-input.")


@h.generator
def FineInterp(_: PiParams) -> h.Module:
    """# MSB Mux
    Generates pair of outputs "early clock" and "late clock" `eck` and `lck` dictated by `sel`."""

    InterpTriInv = TriInv(width=1)

    @h.module
    class FineInterp:
        # IO Interface
        VDD, VSS = h.Ports(2)
        sel = h.Input(width=3, desc="Binary-Encoded Three-Bit Selection input")
        eck, lck = h.Inputs(2, width=1, desc="Early & Late Clock Inputs")
        out = h.Output(width=1, desc="Clock output")

        # Internal Implementation
        ## Binary to Thermometer Encoding
        therm = h.Signal(width=8, desc="Thermometer Encoded Selection Input")
        thermb = h.Signal(width=8, desc="Inverted `therm`")
        tinvs = 8 * Inv()(i=therm, z=thermb, VDD=VDD, VSS=VSS)
        encoder = ThermoEncoder3to8(bin=sel, out=therm, en=VDD, VDD=VDD, VSS=VSS)

        ## Main Event: the interpolation tristate inverters
        outb = h.Signal()
        einvs = 8 * InterpTriInv(i=eck, en=thermb, z=outb, VDD=VDD, VSS=VSS)
        linvs = 8 * InterpTriInv(i=lck, en=therm, z=outb, VDD=VDD, VSS=VSS)
        oinv = InterpTriInv(i=outb, en=VDD, z=out, VDD=VDD, VSS=VSS)

        ## Load Caps
        clb = Cap(Cap.Params(c=50 * f))(p=outb, n=VSS)
        clo = Cap(Cap.Params(c=10 * f))(p=out, n=VSS)

    return FineInterp


@h.generator
def MsbMux(_: PiParams) -> h.Module:
    """# MSB Mux
    Generates pair of outputs "early clock" and "late clock" `eck` and `lck` dictated by `sel`."""

    @h.module
    class MsbMux:
        # IO Interface
        VDD, VSS = h.Ports(2)
        ckq = QuadClock(role=QuadClock.Roles.SINK, port=True, desc="Quadrature input")
        sel = h.Input(width=2, desc="Binary-Encoded Two-Bit Selection input")
        eck, lck = h.Outputs(2, width=1, desc="Early & Late Clock Outputs")

        # Internal Contents
        eckb, lckb = h.Signals(2, width=1, desc="Inverted Early & Late Clocks")
        clb = 2 * Cap(Cap.Params(c=10 * f))(p=h.Concat(eckb, lckb), n=VSS)
        clo = 2 * Cap(Cap.Params(c=10 * f))(p=h.Concat(eck, lck), n=VSS)
        ## One-Hot Select Encoding
        onehot = h.Signal(width=4)
        encoder = OneHotEncoder(width=2)(bin=sel, out=onehot, en=VDD, VDD=VDD, VSS=VSS)

    early = [MsbMux.ckq.ck0, MsbMux.ckq.ck90, MsbMux.ckq.ck180, MsbMux.ckq.ck270]
    late = [MsbMux.ckq.ck90, MsbMux.ckq.ck180, MsbMux.ckq.ck270, MsbMux.ckq.ck0]

    def triinv():
        """Closure to generate a "partial instance" of `TriInv`,
        with the shared connections among all stages."""
        return TriInv(width=1)(VDD=MsbMux.VDD, VSS=MsbMux.VSS)

    def add_pair(index: int):
        """Closure to add a pair of `TriInv`, one each to the early and late clock outputs."""
        i = triinv()(i=early[index], z=MsbMux.eckb, en=MsbMux.onehot[index])
        MsbMux.add(val=i, name=f"einv{index}")
        i = triinv()(i=late[index], z=MsbMux.lckb, en=MsbMux.onehot[index])
        MsbMux.add(val=i, name=f"late{index}")

    # Add four such pairs
    [add_pair(idx) for idx in range(4)]

    # FIXME: doing this with arrays and concatenations would be nice, but is blocked by https://github.com/dan-fritchman/Hdl21/issues/21
    # early = h.Concat(*early)
    # late = h.Concat(*late)

    # # Create the two main tristate-inverter Muxes
    # MsbMux.emux = 4 * TriInv(width=1)(
    #     i=early, z=MsbMux.eckb, en=MsbMux.onehot, VDD=MsbMux.VDD, VSS=MsbMux.VSS
    # )
    # MsbMux.lmux = 4 * TriInv(width=1)(
    #     i=early, z=MsbMux.eckb, en=MsbMux.onehot, VDD=MsbMux.VDD, VSS=MsbMux.VSS
    # )

    # Create the output inverters
    MsbMux.ioe = TriInv(width=1)(
        i=MsbMux.eckb, z=MsbMux.eck, en=MsbMux.VDD, VDD=MsbMux.VDD, VSS=MsbMux.VSS
    )
    MsbMux.iol = TriInv(width=1)(
        i=MsbMux.lckb, z=MsbMux.lck, en=MsbMux.VDD, VDD=MsbMux.VDD, VSS=MsbMux.VSS
    )

    # And voila!
    return MsbMux


@h.generator
def PhaseInterp(p: PiParams) -> h.Module:
    """Phase Interpolator Generator"""

    @h.module
    class PhaseInterp:
        # IO Interface
        VDD, VSS = h.Ports(2)

        ckq = QuadClock(
            role=QuadClock.Roles.SINK, port=True, desc="Quadrature clock input"
        )
        out = Diff(port=True, role=Diff.Roles.SOURCE, desc="Output clock")
        sel = h.Input(width=p.nbits, desc="Selection input")

        # Internal Implementation
        eck, lck = h.Signals(2, width=1, desc="Early & Late MSB Clocks")
        ## MSB Selection Mux
        msb_mux = MsbMux(p)(ckq=ckq, sel=sel[-2:], eck=eck, lck=lck, VDD=VDD, VSS=VSS)
        ## LSB / Fine Interpolator
        ### FIXME: driving differential/ complementary output
        fine = FineInterp(p)(
            eck=eck, lck=lck, sel=sel[:-2], out=out.p, VDD=VDD, VSS=VSS
        )

    return PhaseInterp
