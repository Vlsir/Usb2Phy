""" 
# Phase Interpolator 
## Unit Tests 
"""

# Std-Lib Imports
from copy import copy
from pathlib import Path

# PyPi Imports
import numpy as np
import matplotlib.pyplot as plt

# Hdl & PDK Imports
import sitepdks as _
import s130
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.sim import Sim, LinearSweep, SaveMode
from hdl21.prefix import m, n, PICO
from hdl21.primitives import Vpulse, Vdc

# DUT Imports
from . import PhaseInterp
from .. import QuadClock
from ...diff import Diff
from ...tests.quadclockgen import QuadClockGen, QclkParams
from ...tests.sim_options import sim_options


@h.paramclass
class TbParams:
    VDD = h.Param(dtype=h.Prefixed, desc="Supply Voltage Value")
    code = h.Param(dtype=int, desc="PI Code")


@h.generator
def PhaseInterpTb(p: TbParams) -> h.Module:
    """ Phase Interpolator Testbench """

    tb = h.sim.tb("PhaseInterpTb")

    # Generate the input quadrature clock
    tb.ckq = ckq = QuadClock()
    ckp = QclkParams(v1=0 * m, v2=p.VDD, period=2 * n, trf=100 * PICO)
    tb.ckgen = QuadClockGen(ckp)(ckq=ckq, VSS=tb.VSS)

    # Generate and drive VDD
    tb.VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=p.VDD))(p=tb.VDD, n=tb.VSS)

    # Set up the select/ code input
    tb.code = h.Signal(width=5)

    def vbit(i: int):
        """ Create a `Vdc` call equal to either `p.VDD` or zero. """
        val = p.VDD if i else 0 * m
        return Vdc(Vdc.Params(dc=val))

    def vcode(code: int) -> None:
        """ Closure to drive `tb.code` to the (binary) value of `code`. 
        Essentially an integer to binary, and then binary to `Vdc.Params` converter. """

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

    tb.dck = Diff()
    tb.dut = PhaseInterp(nbits=5)(
        VDD=tb.VDD, VSS=tb.VSS, ckq=tb.ckq, sel=tb.code, out=tb.dck
    )
    return tb


def sim_phase_interp(code: int = 11) -> float:
    """ Phase Interpolator Delay Sim """

    print(f"Simulating PhaseInterp for code {code}")

    tb = PhaseInterpTb(VDD=1800 * m, code=code)

    # Craft our simulation stimulus
    sim = Sim(tb=tb, attrs=s130.install.include(Corner.TYP))
    sim.tran(tstop=10 * n)

    # FIXME: eventually this can be a simulator-internal `Sweep`
    # p = sim.param(name="code", val=0)
    # sim.sweepanalysis(inner=[tr], var=p, sweep=LinearSweep(0, 1, 2), name="mysweep")
    # sim.save(SaveMode.ALL)
    # sim.meas(analysis=tr, name="a_delay", expr="trig_targ_vcode")

    # The delay measurement
    sim.literal(
        f"""
        simulator lang=spice
        .measure tran tdelay when V(xtop:dck_p)=900m rise=2 td=3n
        .option autostop
        simulator lang=spectre
    """
    )

    sim.include("../scs130lp.sp")  # FIXME! relies on this netlist of logic cells
    opts = copy(sim_options)
    opts.rundir = Path(f"./scratch/code{code}")

    results = sim.run(opts)

    print(results.an[0].measurements)
    # And return the delay value
    return results.an[0].measurements["tdelay"]


def test_phase_interp():
    """ Phase Interpolator Test(s) """
    from .compare import save_plot

    delays = [sim_phase_interp(code) for code in range(32)]
    print(delays)
    save_plot(delays, "CMOS PI", "cmospi.png")
