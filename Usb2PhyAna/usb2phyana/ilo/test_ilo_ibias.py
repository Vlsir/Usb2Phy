""" 
# ILO Tests 
"""

import pickle
from typing import List, Tuple, Optional
from dataclasses import asdict
from copy import copy
from pathlib import Path

from pydantic.dataclasses import dataclass
import numpy as np
import matplotlib.pyplot as plt

# Hdl & PDK Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.pdk import Corner
from hdl21.sim import Sim, LogSweep
from hdl21.prefix import m, µ, f, n, T, PICO
from hdl21.primitives import Vdc, Vpulse, Idc, C
import s130
import sitepdks as _

from ..tests.sim_options import sim_options

# DUT Imports
from .tb import Pvt, TbParams, IloFreqTb, sim_input


ibs = [val * µ for val in range(100, 300, 10)]
result_pickle_file = "cmosilo.freq.pkl"


@dataclass
class Result:
    """Result of a corner sweep"""

    # Pvt Conditions
    conditions: List[Pvt]
    # Bias Current per PVT Condition
    ibs: List[h.Prefixed]
    # Sim Results, per Vdd Point
    results: List[List[hs.SimResult]]


def run_corners(tbgen: h.Generator) -> Result:
    """Run `sim` on `tbgen`, across corners"""

    opts = copy(sim_options)
    opts.rundir = None

    # Initialize our results
    conditions = [
        Pvt(p, v, t)
        for p in [Corner.TYP, Corner.FAST, Corner.SLOW]
        for v in [1620 * m, 1800 * m, 1980 * m]
        for t in [-25, 25, 75]
    ]
    result = Result(conditions=conditions, ibs=ibs, results=[])

    # Run conditions one at a time, parallelizing across bias currents
    for cond in conditions:
        print(f"Simulating (ib, freq) for {cond}")
        condition_results = ibias_sweep(tbgen, cond)
        result.results.append(condition_results)

    pickle.dump(asdict(result), open(result_pickle_file, "wb"))
    return result


def ibias_sweep(tbgen: h.Generator, pvt: Pvt) -> List[hs.SimResult]:
    """Sweep `sim` on `tbgen` at conditions `pvt`."""

    opts = copy(sim_options)
    opts.rundir = None

    params = [TbParams(pvt=pvt, ib=ib) for ib in ibs]

    # Create the simulation inputs
    sims = [sim_input(tbgen=tbgen, params=p) for p in params]

    # Run sims
    return h.sim.run(sims, opts)


def plot(result: Result, title: str, fname: str):

    fig, ax = plt.subplots()
    # ax2 = ax.twinx()
    ibs = np.array([1e6 * float(v) for v in result.ibs])

    for (cond, cond_results) in zip(result.conditions, result.results):
        # Post-process the results into (vdd, period) curves
        freqs = np.array([1 / tperiod(r) for r in cond_results])
        idds = np.array([abs(idd(r)) for r in cond_results])

        # Numpy interpolation requires the x-axis array be NaN-free
        # This often happens at low Vdd, when the ring fails to oscillate,
        # or goes slower than we care to simulate.
        # Replace any such NaN values with zero.
        # If there are any later in the array, this interpolation will fail.
        freqs_no_nan = np.nan_to_num(freqs, copy=True, nan=0)
        ib_480 = np.interp(x=480e6, xp=freqs_no_nan, fp=ibs)
        idd_480 = np.interp(x=480e6, xp=freqs_no_nan, fp=idds)
        print(cond, ib_480)

        # And plot the results
        label = f"{str(cond.p), str(cond.v.number), str(cond.t)}"
        ax.plot(ibs, freqs / 1e9, label=label)
        # ax2.plot(freqs / 1e9, ibs)

    # Set up all the other data on our plot
    ax.set_title(title)
    ax.set_ylabel("Freq (GHz)")
    ax.set_xlabel("Ibias (µA)")
    # ax2.set_ylabel("Vdd (mV)")
    # ax.legend()

    # And save it to file
    fig.savefig(fname)


def idd(results: hs.SimResult) -> float:
    return results.an[0].measurements["idd"]


def tperiod(results: hs.SimResult) -> float:
    return results.an[0].measurements["tperiod"]


def test_ilo_freq():
    """Ilo Frequence Test(s)"""

    # Run corner simulations to get results
    result = run_corners(IloFreqTb)

    # Or just read them back from file, if we have one
    result = Result(**pickle.load(open(result_pickle_file, "rb")))

    # And make some pretty pictures
    plot(result, "Cmos Ilo Freq vs Ibias", "CmosIloFreqIbias.png")
