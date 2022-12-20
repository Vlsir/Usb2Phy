""" 
# CML RO Tests 
"""

import pickle, io
from typing import List
from dataclasses import asdict
from copy import copy

from pydantic.dataclasses import dataclass
import numpy as np
import matplotlib.pyplot as plt

# Hdl & PDK Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.pdk import Corner
from hdl21.sim import Sim, LogSweep
from hdl21.prefix import m, µ, f, n, p, T, K
from hdl21.primitives import Vdc, Vpulse, Idc, C
import s130
import sitepdks as _

# Local Imports
from ...tests.sim_options import sim_options

# from ...tests.vcode import VCode
from ...cmlparams import CmlParams
from ..cmlro import CmlRo, CmlIlDco


# Module-wide reused param values
cml = CmlParams(rl=30 * K, cl=10 * f, ib=30 * µ)
ibs = [val * µ for val in range(5, 50, 5)]
rls = [cml.rl] * len(ibs)
# rls = [1.0 / float(ib) for ib in ibs]
results_pickle_file = "scratch/cmlro.freq.pkl"


@h.paramclass
class Pvt:
    """Process, Voltage, and Temperature Parameters"""

    p = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    v = h.Param(dtype=h.Prefixed, desc="Supply Voltage Value (V)", default=1800 * m)
    t = h.Param(dtype=int, desc="Simulation Temperature (C)", default=25)


@h.paramclass
class TbParams:
    # Required CML Generator Params
    cml = h.Param(dtype=CmlParams, desc="Cml Generator Parameters")
    # PVT Conditions
    pvt = h.Param(
        dtype=Pvt, desc="Process, Voltage, and Temperature Parameters", default=Pvt()
    )


@h.generator
def CmlRoFreqTb(params: TbParams) -> h.Module:
    """CmlRo Frequency Testbench"""

    # Create our testbench
    tb = h.sim.tb("CmlRoTb")

    # Generate and drive VDD
    tb.VDD = VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=params.pvt.v, ac=0 * m))(p=VDD, n=tb.VSS)

    # Bias Generation
    # Pmos Side Bias
    tb.pbias = pbias = h.Signal()
    tb.ii = Idc(Idc.Params(dc=params.cml.ib))(p=pbias, n=tb.VSS)
    # Nmos Side Bias
    # tb.nbias = nbias = h.Signal()
    # tb.ii = Idc(Idc.Params(dc=-1 * params.cml.ib))(p=nbias, n=tb.VSS)

    # Signals for the RO stages
    tb.stg0 = stg0 = h.Diff()
    tb.stg1 = stg1 = h.Diff()
    tb.stg2 = stg2 = h.Diff()
    tb.stg3 = stg3 = h.Diff()

    # Create the DUT
    tb.dut = CmlRo(params.cml)(
        stg0=stg0, stg1=stg1, stg2=stg2, stg3=stg3, pbias=pbias, VDD=VDD, VSS=tb.VSS
    )

    return tb


def sim_input(tbgen: h.Generator, params: TbParams) -> hs.Sim:
    """CmlRo Frequency Sim"""

    # Create some simulation stimulus
    @hs.sim
    class CmlRoSim:
        # The testbench
        tb = tbgen(params)

        # op = hs.Op()

        # Our sole analysis: transient, for much longer than we need.
        # But auto-stopping when measurements complete.
        tr = hs.Tran(tstop=500 * n)

        # Measurements
        trise5 = hs.Meas(
            tr, expr="when 'V(xtop.dut.stg0_p)-V(xtop.dut.stg0_n)'=0 rise=5"
        )
        trise15 = hs.Meas(
            tr, expr="when 'V(xtop.dut.stg0_p)-V(xtop.dut.stg0_n)'=0 rise=15"
        )
        tperiod = hs.Meas(tr, expr="param='(trise15-trise5)/10'")
        idd = hs.Meas(tr, expr="avg I(xtop.vvdd) from=trise5 to=trise15")

        # The stuff we can't first-class represent, and need to stick in a literal.
        l = hs.Literal(
            f"""
            simulator lang=spice
            .ic xtop.stg0_p 900m
            .ic xtop.stg0_n 0
            .temp {params.pvt.t}
            .option autostop
            simulator lang=spectre
        """
        )

        i = hs.Include(s130.resources / "stdcells.sp")

        op = hs.Op()

    # Add the PDK dependencies
    CmlRoSim.add(*s130.install.include(params.pvt.p))

    return CmlRoSim


def ibias_sweep(tbgen: h.Generator, pvt: Pvt) -> List[hs.SimResult]:
    """Sweep `sim` on `tbgen` at conditions `pvt`."""

    opts = copy(sim_options)
    opts.rundir = None

    params = [
        TbParams(pvt=pvt, cml=CmlParams(ib=i, rl=r, cl=10 * f))
        for (i, r) in zip(ibs, rls)
    ]

    # Create the simulation inputs
    sims = [sim_input(tbgen=tbgen, params=p) for p in params]

    # Run sims
    return h.sim.run(sims, opts)


@dataclass
class Result:
    """Result of the (I,F) Sweep, Parameterized across Process and Temp"""

    # Process, Temperature Conditions
    conditions: List[Pvt]
    # List of bias currents and resistive loads, maintaining swing
    ibs: List[h.Prefixed]
    rls: List[h.Prefixed]
    # Sim Results, per (P,T), per (ib,rl) Point
    results: List[List[hs.SimResult]]


def run_corners(tbgen: h.Generator) -> Result:
    """Run `sim` on `tbgen`, across corners"""

    # Initialize our results
    conditions = [
        Pvt(p, v, t)
        for p in [Corner.TYP, Corner.FAST, Corner.SLOW]
        for v in [1620 * m, 1800 * m, 1980 * m]
        for t in [-25, 25, 75]
    ]
    result = Result(conditions=conditions, ibs=ibs, rls=rls, results=[])

    # Run conditions one at a time, parallelizing across bias currents
    for cond in conditions:
        print(f"Simulating (ib, freq) for {cond}")
        condition_results = ibias_sweep(tbgen, cond)
        result.results.append(condition_results)

    pickle.dump(asdict(result), open(results_pickle_file, "wb"))
    return result


def plot(result: Result, title: str, fname: str):
    """Plot a `Result` and save to file `fname`"""

    fig, ax = plt.subplots()
    ibs = np.array([1e6 * float(v) for v in result.ibs])

    for (cond, cond_results) in zip(result.conditions, result.results):
        # Post-process the results into (ib, period) curves
        freqs = np.array([1 / tperiod(r) for r in cond_results])
        print(freqs)
        if np.max(freqs) < 480e6:
            print(cond)
        idds = np.abs(np.array([1e6 * idd(r) for r in cond_results]))

        # Numpy interpolation requires the x-axis array be NaN-free
        # This often happens at low Vdd, when the ring fails to oscillate,
        # or goes slower than we care to simulate.
        # Replace any such NaN values with zero.
        # If there are any later in the array, this interpolation will fail.
        freqs_no_nan = np.nan_to_num(freqs, copy=True, nan=0)
        idd_480 = np.interp(x=480e6, xp=freqs_no_nan, fp=idds)
        ib_480 = np.interp(x=480e6, xp=freqs_no_nan, fp=ibs)
        # print(ib_480, idd_480, idd_480 / ib_480)

        # And plot the results
        label = f"{str(cond.p), str(cond.v.number), str(cond.t)}"
        ax.plot(ibs, freqs / 1e9, label=label)

    # Set up all the other data on our plot
    ax.grid()
    ax.set_title(title)
    ax.set_xlabel("Ib (µA)")
    ax.set_ylabel("Freq (GHz)")
    ax.legend()

    # And save it to file
    fig.savefig(fname)


def idd(results: hs.SimResult) -> float:
    return results.an[0].measurements["idd"]


def tperiod(results: hs.SimResult) -> float:
    return results.an[0].measurements["tperiod"]


def run_typ():
    """Run a typical-case sim"""

    print("Running Typical Conditions")
    params = TbParams(pvt=Pvt(), cml=cml)  ##(p=Corner.FAST, v=1980*m, t=75),
    results = sim_input(CmlRoFreqTb, params).run(sim_options)

    print("Typical Conditions:")
    print(results)


def run_and_plot_corners():
    # # Run corner simulations to get results
    # result = run_corners(CmlRoFreqTb)

    # Or just read them back from file, if we have one
    result = Result(**pickle.load(open(results_pickle_file, "rb")))

    # And make some pretty pictures
    plot(result, "Cml Ro - Freq vs Ibias", "scratch/CmlRoFreqIbias.png")


from ...tests.sim_test_mode import SimTestMode


def test_cml_freq(simtestmode: SimTestMode):
    """CmlRo Frequence Test(s)"""

    if simtestmode == SimTestMode.MAX:
        run_and_plot_corners()
    elif simtestmode == SimTestMode.NETLIST:
        params = TbParams(pvt=Pvt(), cml=CmlParams(rl=25 * K, cl=10 * f, ib=40 * µ))
        h.netlist(CmlRoFreqTb(params), dest=io.StringIO())
    else:
        run_typ()
