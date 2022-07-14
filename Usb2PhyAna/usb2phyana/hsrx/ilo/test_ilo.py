
""" 
# ILO Tests 
"""

import pickle
from typing import List, Tuple 
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

from ...tests.sim_options import sim_options

# DUT Imports
from .ilo import Ilo, IloParams


@h.paramclass
class Pvt:
    """ Process, Voltage, and Temperature Parameters """

    p = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    v = h.Param(dtype=h.Prefixed, desc="Supply Voltage Value (V)", default=1800*m)
    t = h.Param(dtype=int, desc="Simulation Temperature (C)", default=25)


@h.paramclass
class TbParams:
    pvt = h.Param(dtype=Pvt, desc="Process, Voltage, and Temperature Parameters", default=Pvt())
    ilo = h.Param(dtype=IloParams, desc="Ilo Generator Parameters", default=IloParams())


@h.generator
def IloInjectionTb(params: TbParams) -> h.Module:
    """ Ilo Testbench """

    # Create our testbench 
    tb = h.sim.tb("IloTb")

    # Generate and drive VDD
    tb.VDD = VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=params.pvt.v))(p=VDD, n=tb.VSS)

    # Create the injection-pulse source, 
    # which also serves as our kick-start
    tb.inj = h.Signal()
    tb.vinj = Vpulse(Vpulse.Params(
            v1=0,
            v2=1800*m,
            period=9900 * PICO,
            rise=10 * PICO,
            fall=10 * PICO,
            width=1500 * PICO,
            delay=0)
        )(p=tb.inj, n=tb.VSS)

    # Create the Ilo DUT 
    tb.dut = Ilo(params.ilo)(
         inj=tb.inj, VDD18=VDD, VSS=tb.VSS,
    )
    return tb


def test_ilo_sim():
    """ Ilo Test(s) """

    # Create our parametric testbench 
    params = TbParams(pvt=Pvt(v=900*m), cl = 30*f)
    tb = IloInjectionTb(params)

    # And simulation input for it 
    sim = Sim(tb=tb, attrs=s130.install.include(Corner.TYP))
    sim.tran(tstop=20*n)
    
    # Run some spice
    results = sim.run(sim_options)
    print(results)


@h.generator
def IloFreqTb(params: TbParams) -> h.Module:
    """ Ilo Frequency Testbench """

    # Create our testbench 
    tb = h.sim.tb("IloTb")

    # Generate and drive VDD
    tb.VDD = VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=params.pvt.v))(p=VDD, n=tb.VSS)

    # Create the injection-pulse source, which in this bench serves entirely as a kick-start
    tb.inj = h.Signal()
    tb.vinj = Vpulse(Vpulse.Params(
            v1=1800*m,
            v2=0,
            period=1001, # "Infinite" period
            rise=10 * PICO,
            fall=10 * PICO,
            width=1000,
            delay=10 * PICO)
        )(p=tb.inj, n=tb.VSS)

    # Create the Ilo DUT 
    tb.dut = Ilo(params.ilo)(
         inj=tb.inj, VDD18=VDD, VSS=tb.VSS,
    )
    return tb


@dataclass 
class Result:
    """ Result of the (V,F) Sweep, Parameterized across Process and Temp """

    # Process, Temperature Conditions 
    conditions: List[Tuple[Corner, int]]
    # Vdds per Process, Temperature Condition
    vdds: List[h.Prefixed]
    # Sim Results, per Vdd Point 
    results: List[List[hs.SimResult]]


def run_corners(tbgen: h.Generator) -> Result:
    """ Run `sim` on `tbgen`, across corners """

    opts = copy(sim_options)
    opts.rundir = None

    # (P,T) Conditions 
    conditions = [{
            "p": corner,
            "t": temper,
        }
        for corner in [Corner.TYP, Corner.FAST, Corner.SLOW]
        for temper in [-25, 25, 75]
    ]

    # Initialize our results
    result = Result(
        conditions=[(cond["p"], cond["t"]) for cond in conditions], 
        vdds = [val*m for val in range(200, 2100, 100)],
        results=[]
    )

    # Run conditions one at a time, parallelizing across PI codes
    for cond in conditions:
        print(f"Simulating (vdd, freq) for {cond}")

        # Create a list of per-voltage tb parameters
        params = [TbParams(
            pvt=Pvt(v=v, **cond), 
            ilo=IloParams(cl=30*f)
        ) for v in result.vdds]
        
        # Create the simulation inputs
        sims = [sim_input(tbgen=tbgen, params=p) for p in params]

        # Run sims
        condition_results = h.sim.run(sims, opts)
        result.results.append(condition_results)

    
    pickle.dump(asdict(result), open("result.pkl", "wb"))

    return result

def plot(result: Result, title: str, fname: str):

    fig, ax = plt.subplots()
    ax2 = ax.twinx()
    vdds = np.array([1000 * float(v) for v in result.vdds])

    for (cond, cond_results) in zip(result.conditions, result.results):
        # Post-process the results into (vdd, period) curves
        freqs = np.array([1 / tperiod(r) for r in cond_results])
        idds = np.array([idd(r) for r in cond_results])

        # Numpy interpolation requires the x-axis array be NaN-free
        # This often happens at low Vdd, when the ring fails to oscillate, 
        # or goes slower than we care to simulate. 
        # Replace any such NaN values with zero. 
        # If there are any later in the array, this interpolation will fail. 
        freqs_no_nan = np.nan_to_num(freqs, copy=True, nan=0)
        idd_480 = np.interp(x=480e6, xp=freqs_no_nan, fp=idds)
        vdd_480 = np.interp(x=480e6, xp=freqs_no_nan, fp=vdds)
        print(cond, vdd_480, idd_480)

        # And plot the results
        label = str(cond) ##f"{cond[0], cond[1]}" ## FIXME! f"{params.pvt.corner} {params.pvt.temper}"
        ax.plot(freqs / 1e9, np.abs(idds), label=label)
        ax2.plot(freqs / 1e9, vdds)
    
    # Set up all the other data on our plot
    ax.set_title(title)
    ax.set_xlabel("Freq (GHz)")
    ax.set_ylabel("Idd (A)")
    ax2.set_ylabel("Vdd (mV)")
    ax.legend()

    # And save it to file
    fig.savefig(fname)


def idd(results: "SimResult") -> float:
    return results.an[0].measurements["idd"]

def tperiod(results: "SimResult") -> float:
    return results.an[0].measurements["tperiod"]


def sim_input(tbgen: h.Generator, params: TbParams) -> hs.Sim:
    """ Ilo Frequency Sim """

    print(f"Simulating Ilo for voltage {params.pvt.v}")

    # Create some simulation stimulus
    @hs.sim
    class IloSim:
        # The testbench 
        tb = tbgen(params)

        # Our sole analysis: transient, for much longer than we need. 
        # But auto-stopping when measurements complete. 
        tr = hs.Tran(tstop=500 * n)

        # Measurements
        trise5 = hs.Meas(tr, expr="when 'V(xtop.dut.stg0_p)-V(xtop.dut.stg0_n)'=0 rise=5")
        trise15 = hs.Meas(tr, expr="when 'V(xtop.dut.stg0_p)-V(xtop.dut.stg0_n)'=0 rise=15")
        tperiod = hs.Meas(tr, expr="param='(trise15-trise5)/10'")
        idd = hs.Meas(tr, expr="avg I(xtop.vvdd) from=trise5 to=trise15")

        # The stuff we can't first-class represent, and need to stick in a literal. 
        _ = hs.Literal(
            f"""
            simulator lang=spice
            .temp {params.pvt.t}
            .option autostop
            simulator lang=spectre
        """) 

    # Add the PDK dependencies 
    IloSim.add(*s130.install.include(params.pvt.p))

    # # FIXME: handling of multi-directory sims
    # opts = copy(sim_options)
    # opts.rundir = Path(f"./scratch/")
    
    return IloSim


def test_ilo_freq():
    """ Ilo Frequence Test(s) """

    # Run corner simulations to get results 
    result = run_corners(IloFreqTb)

    # Or just read them back from file, if we have one
    # result = Result(**pickle.load(open("result.pkl", "rb")))

    # And make some pretty pictures
    plot(result, "IloFreq", "IloFreq.png")


