""" 
# Phase Interpolator 
## Testbench & Unit Tests
"""

import io

# Hdl & PDK Imports
import hdl21 as h
from hdl21 import Diff
from hdl21.prefix import m, n, PICO
from hdl21.primitives import Vdc

# DUT Imports
from . import PhaseInterp
from .tb import TbParams, tdelay
from ...quadclock import QuadClock
from ...tests.quadclockgen import QuadClockGen, QclkParams
from ...tests.sim_options import sim_options


@h.generator
def PhaseInterpTb(p: TbParams) -> h.Module:
    """Phase Interpolator Testbench"""

    tb = h.sim.tb("PhaseInterpTb")

    # Generate the input quadrature clock
    tb.ckq = ckq = QuadClock()
    ckp = QclkParams(v1=0 * m, v2=p.VDD, period=2 * n, trf=100 * PICO)
    tb.ckgen = QuadClockGen(ckp)(ckq=ckq, VSS=tb.VSS)

    # Generate and drive VDD
    tb.VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=p.VDD, ac=0 * m))(p=tb.VDD, n=tb.VSS)

    # Set up the select/ code input
    tb.code = h.Signal(width=5)

    def vbit(i: int):
        """Create a `Vdc` call equal to either `p.VDD` or zero."""
        val = p.VDD if i else 0 * m
        return Vdc(Vdc.Params(dc=val, ac=0 * m))

    def vcode(code: int) -> None:
        """Closure to drive `tb.code` to the (binary) value of `code`.
        Essentially an integer to binary, and then binary to `Vdc.Params` converter."""

        if code < 0:
            raise ValueError

        # Convert to a binary-valued string
        bits = bin(code)[2:].zfill(tb.code.width)

        # And create a voltage source for each bit
        for idx in range(5):
            bitval = int(bits[-(idx + 1)])
            vinst = vbit(bitval)(p=tb.code[idx], n=tb.VSS)
            tb.add(name=f"vcode{idx}", val=vinst)

    # Call all that to drive the code bus
    vcode(p.code)

    # Create the differential output clock
    tb.dck = Diff()
    # And since this version really only drives single ended, drive the negative half to VDD/2
    tb.vdckn = Vdc(Vdc.Params(dc=p.VDD / 2, ac=0 * m))(p=tb.dck.n, n=tb.VSS)

    # Finally, create the DUT
    tb.dut = PhaseInterp(nbits=5)(
        VDD=tb.VDD, VSS=tb.VSS, ckq=tb.ckq, sel=tb.code, out=tb.dck
    )
    return tb


from ...tests.sim_test_mode import SimTestMode


def test_phase_interp(simtestmode: SimTestMode):
    """Phase Interpolator Test(s)"""

    from .tb import sim_input
    from .compare import save_plot

    if simtestmode == SimTestMode.NETLIST:
        p = TbParams(code=15)
        h.netlist(PhaseInterpTb(p), dest=io.StringIO())
    elif simtestmode == SimTestMode.MIN:
        # Just run one code
        p = TbParams(code=15)
        sim_input(tb=PhaseInterpTb(p), params=p).run()
    else:
        params = [TbParams(code=code) for code in range(32)]

        # Create the simulation inputs
        sims = [sim_input(tb=PhaseInterpTb(p), params=p) for p in params]

        # Run sims
        results = h.sim.run(sims, opts=sim_options)

        delays = [tdelay(r) for r in results]
        save_plot(delays, "CMOS PI", "cmospi.png")
