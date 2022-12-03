""" 
# Cmos Ilo Dac Code Sweep 
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
from hdl21.prefix import m, µ, f, K

# Local Imports
from .tb import IloFreqTb, Pvt, TbParams, sim_input
from ..tests.sim_options import sim_options


# Module-wide reused parameters
result_pickle_file = "scratch/cmosilo.dac_code.pkl"
codes = list(range(0, 32))


@dataclass
class Result:
    # Pvt Conditions
    conditions: List[Pvt]
    # List of Dac codes simulated
    codes: List[int]
    # Sim Results, per PVT, per code
    results: List[List[hs.SimResult]]


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
        condition_results = codesweep(tbgen, pvt)
        result.results.append(condition_results)

    pickle.dump(asdict(result), open(result_pickle_file, "wb"))
    return result


def codesweep(tbgen: h.Generator, pvt: Pvt) -> List[hs.SimResult]:
    """Run `sim` on `tbgen`, across codes, at conditions `pvt`."""

    opts = copy(sim_options)
    opts.rundir = None

    params = [TbParams(pvt=pvt, code=code) for code in codes]

    # Create the simulation inputs
    sims = [sim_input(tbgen=tbgen, params=p) for p in params]

    # Run sims
    return h.sim.run(sims, opts)


def plot(result: Result, title: str, fname: str):
    """Plot a `Result` and save to file `fname`"""

    fig, ax = plt.subplots()
    codes = np.array(result.codes)

    for (cond, cond_results) in zip(result.conditions, result.results):
        label = f"{str(cond.p), str(cond.v), str(cond.t)}"

        # Post-process the results into (ib, period) curves
        freqs = np.array([1 / tperiod(r) for r in cond_results])
        idds = np.abs(np.array([1e6 * idd(r) for r in cond_results]))

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

    # Set up all the other data on our plot
    ax.grid()
    ax.set_title(title)
    ax.set_xlabel("Dac Code")
    ax.set_ylabel("Freq (MHz)")
    # ax.legend()

    # And save it to file
    fig.savefig(fname)


def idd(results: hs.SimResult) -> float:
    return results.an[0].measurements["idd"]


def tperiod(results: hs.SimResult) -> float:
    return results.an[0].measurements["tperiod"]


def run_one() -> hs.SimResult:
    """Run a typical-case, mid-code sim"""

    print("Running Typical Conditions")
    params = TbParams()
    results = sim_input(IloFreqTb, params).run(sim_options)

    print("Typical Condition Results:")
    print(results)


def run_and_plot_corners():
    # Run corner simulations to get results
    result = run_corners(IloFreqTb)

    # Or just read them back from file, if we have one
    result = Result(**pickle.load(open(result_pickle_file, "rb")))

    # And make some pretty pictures
    plot(result, "Cmos Ilo - Dac vs Freq", "scratch/CmosIloDacFreq.png")


from ..tests.sim_test_mode import SimTestMode


def test_ilo_dac_code(simtestmode: SimTestMode):
    """Cmos Ilo Dac Code vs Frequence Test(s)"""

    if simtestmode == SimTestMode.NETLIST:
        params = TbParams()
        h.netlist(IloFreqTb(params), dest=io.StringIO())
    elif simtestmode == SimTestMode.MIN:
        run_one()
    elif simtestmode == SimTestMode.TYP:
        codesweep(pvt=Pvt())
    else:
        run_and_plot_corners()
