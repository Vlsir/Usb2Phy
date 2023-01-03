""" 
# Cmos Ilo Dac Code Sweep 
"""

import pickle, io
from pathlib import Path
from typing import List
from dataclasses import asdict, replace
from copy import copy

from pydantic.dataclasses import dataclass
import numpy as np
import matplotlib.pyplot as plt

# Hdl & PDK Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.pdk import Corner

# Local Imports
from .tb import IloFreqTb, Pvt, TbParams, sim_input
from ..tests.sim_options import sim_options
from ..tests.sim_test_mode import SimTestMode, SimTest


# Module-wide reused parameters
result_pickle_file = "scratch/cmosilo.dac_code.pkl"
codes = list(range(0, 32))


@dataclass
class SingleSimSummary:
    freq: float
    idd: float

    @classmethod
    def build(cls, sim_result: hs.SimResult) -> "SingleSimSummary":
        freq = 1 / tperiod(sim_result)
        idd_ = abs(1e6 * idd(sim_result))

        # Numpy interpolation requires the x-axis array be NaN-free
        # This often happens at low Vdd, when the ring fails to oscillate,
        # or goes slower than we care to simulate.
        # Replace any such NaN values with zero.
        # If there are any later in the array, this interpolation will fail.
        freq = np.nan_to_num(freq, copy=True, nan=0)
        return SingleSimSummary(freq, idd=idd_)


@dataclass
class ConditionResult:
    # Results at a single PVT condition
    cond: Pvt
    codes: List[int]
    summaries: List[SingleSimSummary]


@dataclass
class Result:
    # Pvt Conditions
    conditions: List[Pvt]
    # List of Dac codes simulated
    codes: List[int]
    # Sim Results, per PVT, per code
    cond_results: List[ConditionResult]


def run_corners(tbgen: h.Generator) -> Result:
    """Run `sim` on `tbgen`, across corners"""

    # Initialize our results
    conditions = [
        Pvt(p, v, t)
        for p in [Corner.TYP, Corner.FAST, Corner.SLOW]
        for v in [Corner.TYP, Corner.FAST, Corner.SLOW]
        for t in [25, 75, -25]
    ]
    result = Result(conditions=conditions, codes=codes, results=[])

    # Run conditions one at a time, parallelizing across codes
    for pvt in conditions:
        print(f"Simulating {pvt}")
        cond_results = codesweep(tbgen, pvt)
        result.cond_results.append(cond_results)

    pickle.dump(asdict(result), open(result_pickle_file, "wb"))
    return result


def codesweep(tbgen: h.Generator, pvt: Pvt) -> ConditionResult:
    """Run `sim` on `tbgen`, across codes, at conditions `pvt`."""

    opts = copy(sim_options)
    opts.rundir = None

    params = [TbParams(pvt=pvt, code=code) for code in codes]

    # Create the simulation inputs
    sims = [sim_input(tbgen=tbgen, params=p) for p in params]

    # Run sims
    sim_results = h.sim.run(sims, opts)
    return ConditionResult(
        cond=pvt,
        codes=codes,
        summaries=[SingleSimSummary.build(s) for s in sim_results],
    )


def plot(result: Result, title: str, fname: str):
    """Plot a `Result` and save to file `fname`"""

    fig, ax = plt.subplots()
    codes = np.array(result.codes)

    for (cond, cond_results) in zip(result.conditions, result.cond_results):
        plot_cond(ax, codes, cond, cond_results)

    # Set up all the other data on our plot
    ax.grid()
    ax.set_title(title)
    ax.set_xlabel("Dac Code")
    ax.set_ylabel("Freq (MHz)")
    # ax.legend()

    # And save it to file
    fig.savefig(fname)


def plot_cond(ax, cond_results: ConditionResult):
    """Add a plot for Pvt condition `cond_results` to `ax`"""
    cond = cond_results.cond
    codes = cond_results.codes
    label = f"{str(cond.p), str(cond.v), str(cond.t)}"

    # Post-process the results into (ib, period) curves
    freqs = np.array([r.freq for r in cond_results.summaries])
    idds = np.array([r.idd for r in cond_results.summaries])

    # Numpy interpolation requires the x-axis array be NaN-free
    # This often happens at low Vdd, when the ring fails to oscillate,
    # or goes slower than we care to simulate.
    # Replace any such NaN values with zero.
    # If there are any later in the array, this interpolation will fail.
    freqs_no_nan = np.nan_to_num(freqs, copy=True, nan=0)
    idd_480 = np.interp(x=480e6, xp=freqs_no_nan, fp=idds)
    # print(idd_480)

    # Check for non-monotonic frequencies
    freq_steps = np.diff(freqs_no_nan)
    if np.any(freq_steps < 0):
        print(cond)
    min_freq = np.min(freqs_no_nan) / 1e6
    max_freq = np.max(freqs_no_nan) / 1e6
    print(label, min_freq, max_freq)
    if min_freq > 480 or max_freq < 480:
        print("OUT OF RANGE")

    # And plot the results
    ax.plot(codes, freqs / 1e6, label=label)


def idd(results: hs.SimResult) -> float:
    return results.an[0].measurements["idd"]


def tperiod(results: hs.SimResult) -> float:
    return results.an[0].measurements["tperiod"]


def run_one() -> hs.SimResult:
    """Run a typical-case, mid-code sim"""

    print("Running Typical Conditions")
    sim_result = sim_input(IloFreqTb, TbParams()).run(
        replace(sim_options, rundir="./scratch")
    )
    print(sim_result.an[1].data)
    summary = SingleSimSummary.build(sim_result)
    print("Typical Condition Results:")
    print(summary)


class TestIloDacCode(SimTest):
    """Cmos Ilo Dac Code vs Frequence Test(s)"""

    tbgen = IloFreqTb

    def min(self):
        """Run a single code at typical conditions"""
        run_one()

    def typ(self):
        """Sweep DAC codes at typical PVT conditions"""
        results = codesweep(tbgen=IloFreqTb, pvt=Pvt())
        fig, ax = plt.subplots()
        plot_cond(ax, results)
        fig.savefig("scratch/codesweep.png")

    def max(self):
        """Sweep DAC codes across PVT conditions"""

        # Run corner simulations to get results
        result = run_corners(IloFreqTb)

        # Or just read them back from file, if we have one
        # result = Result(**pickle.load(open(result_pickle_file, "rb")))

        # And make some pretty pictures
        plot(result, "Cmos Ilo - Dac vs Freq", "scratch/CmosIloDacFreq.png")
