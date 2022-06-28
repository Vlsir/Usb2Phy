""" 
# CML Phase Interpolator 
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
from hdl21.prefix import m, n, PICO, µ, f, K
from hdl21.primitives import Vdc, Idc

# DUT Imports
from ...tests.sim_options import sim_options
from ...tests.quadclockgen import QuadClockGen, QclkParams
from .cmlpi import PhaseInterp
from .. import Diff
from ...cmldiv import CmlBuf, CmlParams
# from .. import QuadClock # FIXME: Sad!


@h.paramclass
class TbParams:
    VDD = h.Param(dtype=h.Prefixed, desc="Supply Voltage Value")
    code = h.Param(dtype=int, desc="PI Code")


@h.generator
def PhaseInterpTb(p: TbParams) -> h.Module:
    """ Phase Interpolator Testbench """

    params = CmlParams(rl=4 * K, cl=25 * f, ib=250 * µ)

    tb = h.sim.tb("PhaseInterpTb")

    # Generate the input quadrature clock
    # tb.ckq = ckq = QuadClock()
    # Sadly we've gotta cobble this together from scalar Signals, for now
    tb.ck0, tb.ck90, tb.ck180, tb.ck270 = h.Signals(4)

    ckq = h.AnonymousBundle(ck0=tb.ck0, ck90=tb.ck90, ck180=tb.ck180, ck270=tb.ck270,)
    ckp = QclkParams(v1=0 * m, v2=p.VDD, period=2 * n, trf=100 * PICO)
    tb.ckgen = QuadClockGen(ckp)(ckq=ckq, VSS=tb.VSS)

    # Generate and drive VDD
    tb.VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=p.VDD))(p=tb.VDD, n=tb.VSS)

    # And create "Diff-like" I and Q bundles
    cki = h.AnonymousBundle(p=tb.ck0, n=tb.ck180,)
    ckq = h.AnonymousBundle(p=tb.ck90, n=tb.ck270,)

    # Buffer both input clocks, pulling them into our CML levels
    tb.ck0buf, tb.ck90buf, tb.ck180buf, tb.ck270buf = h.Signals(4)
    tb.bufbiasi = bufbiasi = h.Signal()
    tb.iibuf = Idc(Idc.Params(dc=-1 * params.ib))(p=bufbiasi, n=tb.VSS)
    tb.ckbufi = CmlBuf(params)(
        i=cki,
        o=h.AnonymousBundle(p=tb.ck0buf, n=tb.ck180buf),
        ibias=bufbiasi,
        VDD=tb.VDD,
        VSS=tb.VSS,
    )
    tb.bufbiasq = bufbiasq = h.Signal()
    tb.iqbuf = Idc(Idc.Params(dc=-1 * params.ib))(p=bufbiasq, n=tb.VSS)
    tb.ckbufq = CmlBuf(params)(
        i=ckq,
        o=h.AnonymousBundle(p=tb.ck90buf, n=tb.ck270buf),
        ibias=bufbiasq,
        VDD=tb.VDD,
        VSS=tb.VSS,
    )

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
    ckqbuf = h.AnonymousBundle(
        ck0=tb.ck0buf, ck90=tb.ck90buf, ck180=tb.ck180buf, ck270=tb.ck270buf,
    )
    tb.dut = PhaseInterp(nbits=5)(
        VDD=tb.VDD, VSS=tb.VSS, ckq=ckqbuf, sel=tb.code, out=tb.dck
    )
    return tb


def sim_phase_interp(code: int = 11) -> float:
    """ Phase Interpolator Delay Sim """

    print(f"Simulating PhaseInterp for code {code}")

    tb = PhaseInterpTb(VDD=1800 * m, code=code)

    # Craft our simulation stimulus
    sim = Sim(tb=tb, attrs=s130.install.include(Corner.TYP))
    sim.include("../scs130lp.sp")  # FIXME! relies on this netlist of logic cells

    opts = copy(sim_options)
    opts.rundir = Path(f"./scratch/code{code}")

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
        .measure tran tdelay when 'V(xtop:dck_p)-V(xtop:dck_n)'=0 rise=2 td=3n
        .option autostop
        simulator lang=spectre
    """
    )
    # .measure tran tdelay trig V(xtop:ckq_ck0) val=900m rise=2 targ V(xtop:dck) val=900m rise=1

    results = sim.run(opts)

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
    plt.plot(delays * 1e12)
    plt.ylabel("Delay (ps)")
    plt.xlabel("PI Code")
    plt.savefig("delays.png")

