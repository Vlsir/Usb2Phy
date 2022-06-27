""" 
# Phase Interpolator 
## Unit Tests 
"""

# Std-Lib Imports
import copy
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
from ...tests.sim_options import sim_options
from . import PhaseInterp
from .. import QuadClock


@h.paramclass
class QclkParams:
    """ Quadrature Clock Generator Parameters """

    period = h.Param(dtype=h.Prefixed, desc="Period")
    v1 = h.Param(dtype=h.Prefixed, desc="Low Voltage Level")
    v2 = h.Param(dtype=h.Prefixed, desc="High Voltage Level")
    trf = h.Param(dtype=h.Prefixed, desc="Rise / Fall Time")


@h.generator
def QuadClockGen(p: QclkParams) -> h.Module:
    """ # Quadrature Clock Generator 
    For simulation, from ideal pulse voltage sources """

    def phpars(idx: int) -> Vpulse.Params:
        """ Closure to create the delay-value for quadrature index `idx`, valued 0-3. 
        Transitions start at 1/8 of a period, so that clocks are stable during time zero. """

        # Delays per phase, in eights of a period.
        # Note the negative values set `val2` as active during simulation time zero.
        vals = [1, 3, -3, -1]
        if idx < 0 or idx > 3:
            raise ValueError

        return Vpulse.Params(
            v1=p.v1,
            v2=p.v2,
            period=p.period,
            rise=p.trf,
            fall=p.trf,
            width=p.period / 2 - p.trf,
            delay=vals[idx] * p.period / 8 - p.trf / 2,
        )

    ckg = h.Module()
    ckg.VSS = VSS = h.Port()

    ckg.ckq = ckq = QuadClock(
        role=QuadClock.Roles.SINK, port=True, desc="Quadrature Clock Output"
    )
    ckg.v0 = Vpulse(phpars(0))(p=ckq.ck0, n=VSS)
    ckg.v90 = Vpulse(phpars(1))(p=ckq.ck90, n=VSS)
    ckg.v180 = Vpulse(phpars(2))(p=ckq.ck180, n=VSS)
    ckg.v270 = Vpulse(phpars(3))(p=ckq.ck270, n=VSS)
    return ckg


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

    tb.dck = h.Signal(width=1)
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
        .measure tran tdelay when V(xtop:dck)=900m rise=2 td=3n
        .option autostop=yes
        simulator lang=spectre
    """
    )
    # .measure tran tdelay trig V(xtop:ckq_ck0) val=900m rise=2 targ V(xtop:dck) val=900m rise=1

    sim.include("../scs130lp.sp")  # FIXME! relies on this netlist of logic cells
    sim_options.rundir = Path(f"./scratch/code{code}")
    results = sim.run(sim_options)

    print(results.an[0].measurements)
    # And return the delay value
    return results.an[0].measurements["tdelay"]


def test_phase_interp():
    """ Phase Interpolator Test(s) """
    delays = [sim_phase_interp(code) for code in range(32)]
    print(delays)

    # Unwrap the period from the delays
    delays = np.array(delays) % float(2 * n)
    amin = np.argmin(delays)
    delays = np.concatenate((delays[amin:], delays[:amin]))
    print(delays)

    # And save a plot of the results
    plt.ioff()
    plt.plot(delays)
    plt.savefig("delays.png")

