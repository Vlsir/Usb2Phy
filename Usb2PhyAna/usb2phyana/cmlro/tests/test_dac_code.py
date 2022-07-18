
""" 
# CML RO DAC Code Sweep 
"""

import pickle
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
from ...tests.sim_options import sim_options
from ...cmlparams import CmlParams
from .tb import Pvt, TbParams, CmlRoFreqTb, sim_input, run_typ


# Module-wide reused parameters 
codes = range(0, 32)  
cml = CmlParams(rl=25 * K, cl=10 * f, ib=40 * µ)


@dataclass 
class Result:
    # Pvt Conditions 
    conditions: List[Pvt]
    # List of Dac codes simulated
    codes: List[int]
    # Sim Results, per PVT, per code
    results: List[List[hs.SimResult]]


def run_corners(tbgen: h.Generator) -> Result:
    """ Run `sim` on `tbgen`, across corners """

    opts = copy(sim_options)
    opts.rundir = None

    # Initialize our results
    conditions=[
        Pvt(p,v,t) 
        for p in [Corner.TYP, Corner.FAST, Corner.SLOW]
        for v in [1620*m, 1800*m, 1980*m]
        for t in [-25, 25, 75]
    ]
    result = Result(
        conditions=conditions, 
        codes=codes,
        results=[]
    )

    # Run conditions one at a time, parallelizing across codes
    for pvt in conditions:
        print(f"Simulating {pvt}")
        condition_results = codesweep(tbgen, pvt)
        result.results.append(condition_results)
    
    pickle.dump(asdict(result), open("cmlro.dac.pkl", "wb"))
    return result


def codesweep(tbgen: h.Generator, pvt: Pvt) -> List[hs.SimResult]:
    """ Run `sim` on `tbgen`, across codes, at conditions `pvt`.  """

    opts = copy(sim_options)
    opts.rundir = None

    params = [
        TbParams(
            pvt=pvt, 
            cml=cml,
            code=code
        ) for code in codes
    ]
    
    # Create the simulation inputs
    sims = [sim_input(tbgen=tbgen, params=p) for p in params]

    # Run sims
    return h.sim.run(sims, opts)


def plot(result: Result, title: str, fname: str):
    """ Plot a `Result` and save to file `fname` """

    fig, ax = plt.subplots()
    codes = np.array(result.codes)

    for (cond, cond_results) in zip(result.conditions, result.results):
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

        # And plot the results
        label = f"{str(cond.p), str(cond.v.number), str(cond.t)}"
        ax.plot(codes, freqs / 1e9, label=label)
    
    # Set up all the other data on our plot
    ax.set_title(title)
    ax.set_xlabel("Dac Code")
    ax.set_ylabel("Freq (GHz)")
    # ax.legend()

    # And save it to file
    fig.savefig(fname)


def idd(results: hs.SimResult) -> float:
    return results.an[0].measurements["idd"]

def tperiod(results: hs.SimResult) -> float:
    return results.an[0].measurements["tperiod"]


def test_cml_dac():
    """ CmlRo Frequence Test(s) """

    run_typ()

    # Run corner simulations to get results 
    result = run_corners(CmlRoFreqTb)

    # Or just read them back from file, if we have one
    result = Result(**pickle.load(open("cmlro.dac.pkl", "rb")))

    # And make some pretty pictures
    plot(result, "CmlRoFreq", "CmlRoDac.png")
