
""" 
# CML RO Tests 
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
from hdl21.prefix import m, µ, f, n, p, T, K
from hdl21.primitives import Vdc, Vpulse, Idc, C
import s130 
import sitepdks as _

# Local Imports
from ...tests.sim_options import sim_options
# from ...tests.vcode import VCode
from ...cmlparams import CmlParams
from ..cmlro import CmlRo, CmlIlDco


@h.paramclass
class Pvt:
    """ Process, Voltage, and Temperature Parameters """

    p = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    v = h.Param(dtype=h.Prefixed, desc="Supply Voltage Value (V)", default=1800*m)
    t = h.Param(dtype=int, desc="Simulation Temperature (C)", default=25)


@h.paramclass
class TbParams:
    # Required CML Generator Params
    cml = h.Param(dtype=CmlParams, desc="Cml Generator Parameters")
    # PVT Conditions 
    pvt = h.Param(dtype=Pvt, desc="Process, Voltage, and Temperature Parameters", default=Pvt())


@h.generator
def CmlRoFreqTb(params: TbParams) -> h.Module:
    """ CmlRo Frequency Testbench """

    # Create our testbench 
    tb = h.sim.tb("CmlRoTb")

    # Generate and drive VDD
    tb.VDD = VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=params.pvt.v))(p=VDD, n=tb.VSS)

    # Bias Generation
    tb.ibias = ibias = h.Signal()
    # Nmos Side Bias
    tb.ii = Idc(Idc.Params(dc=-1 * params.cml.ib))(p=ibias, n=tb.VSS)
    # Pmos Side Bias
    # tb.ii = Idc(Idc.Params(dc=params.cml.ib))(p=ibias, n=tb.VSS)

    # Signals for the RO stages
    tb.stg0 = stg0 = h.Diff()
    tb.stg1 = stg1 = h.Diff()
    tb.stg2 = stg2 = h.Diff()
    tb.stg3 = stg3 = h.Diff()

    # Create the DUT 
    # Dut = CmlRo(params.cml)
    # tb.dut = CmlRo(params.cml)(stg0=stg0, stg1=stg1, stg2=stg2, stg3=stg3, ibias=ibias, VDD=VDD, VSS=tb.VSS)

    # Create the DUT 
    # tb.fctrl = fctrl = h.Signal(width=5)
    fctrl = h.Concat(tb.VDD, tb.VSS, tb.VSS, tb.VSS, tb.VSS)
    tb.refclk = h.Signal()
    # tb.vrefclk = Vpulse(Vpulse.Params(delay=5 * n, v1=0, v2=params.pvt.v, period=32 * n, rise=100 * p, fall=100 * p, width=16 * n))(p=tb.refclk, n=tb.VSS)
    tb.vrefclk = Vdc(Vdc.Params(dc=0))(p=tb.refclk, n=tb.VSS)
    tb.dut = CmlIlDco(params.cml)(stg0=stg0, stg1=stg1, stg2=stg2, stg3=stg3, ibias=ibias, refclk=tb.refclk, fctrl=fctrl, VDD=VDD, VSS=tb.VSS)

    return tb


@dataclass 
class Result:
    """ Result of the (I,F) Sweep, Parameterized across Process and Temp """

    # Process, Temperature Conditions 
    conditions: List[Tuple[Corner, int]]
    # List of bias currents and resistive loads, maintaining swing 
    ibs: List[h.ScalarParam]
    rls: List[h.ScalarParam]
    # Sim Results, per (P,T), per (ib,rl) Point 
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
    ibs = [val * µ for val in range(5, 100, 5)]
    rls = [1.0 / float(i) for i in ibs]
    result = Result(
        conditions=[(cond["p"], cond["t"]) for cond in conditions], 
        ibs = ibs,
        rls = rls,
        results=[]
    )

    # Run conditions one at a time, parallelizing across PI codes
    for cond in conditions:
        print(f"Simulating (ib, freq) for {cond}")

        # Create a list of per-voltage tb parameters
        params = [TbParams(
            pvt=Pvt(v=1800*m, **cond), 
            cml=CmlParams(rl=r, cl=10 * f, ib=i)
        ) for (i, r) in zip(result.ibs, result.rls)]
        
        # Create the simulation inputs
        sims = [sim_input(tbgen=tbgen, params=p) for p in params]

        # Run sims
        condition_results = h.sim.run(sims, opts)
        result.results.append(condition_results)
    
    pickle.dump(asdict(result), open("cmlro.freq.pkl", "wb"))

    return result

def plot(result: Result, title: str, fname: str):

    fig, ax = plt.subplots()
    ax2 = ax.twinx()
    ibs = np.array([1e6 * float(v) for v in result.ibs])

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
        ib_480 = np.interp(x=480e6, xp=freqs_no_nan, fp=ibs)
        print(ib_480, idd_480, idd_480 / ib_480)

        # And plot the results
        label = str(cond) 
        ax.plot(freqs / 1e9, idds, label=label)
        ax2.plot(freqs / 1e9, ibs)
    
    # Set up all the other data on our plot
    ax.set_title(title)
    ax.set_xlabel("Freq (GHz)")
    ax.set_ylabel("Idd (µA)")
    ax.legend()

    # And save it to file
    fig.savefig(fname)


def idd(results: hs.SimResult) -> float:
    return results.an[0].measurements["idd"]

def tperiod(results: hs.SimResult) -> float:
    return results.an[0].measurements["tperiod"]


def sim_input(tbgen: h.Generator, params: TbParams) -> hs.Sim:
    """ CmlRo Frequency Sim """

    # Create some simulation stimulus
    @hs.sim
    class CmlRoSim:
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
        l = hs.Literal(
            f"""
            simulator lang=spice
            .ic xtop.stg0_p 900m
            .ic xtop.stg0_n 0
            .temp {params.pvt.t}
            .option autostop
            simulator lang=spectre
        """) 

        # FIXME! relies on this netlist of logic cells
        i = hs.Include("/tools/B/dan_fritchman/dev/VlsirWorkspace/Usb2Phy/Usb2PhyAna/resources/scs130lp.sp") 

    # Add the PDK dependencies 
    CmlRoSim.add(*s130.install.include(params.pvt.p))

    # # FIXME: handling of multi-directory sims
    # opts = copy(sim_options)
    # opts.rundir = Path(f"./scratch/")
    
    return CmlRoSim


def run_typ():
    """ Run a typical-case sim """
    
    print("Running Typical Conditions")
    params = TbParams(
        pvt=Pvt(), 
        cml=CmlParams(rl=30 * K, cl=10 * f, ib=30 * µ)
    )
    results = sim_input(CmlRoFreqTb, params).run(sim_options)
    
    print("Typical Conditions:")
    print(results)


def test_cml_freq():
    """ CmlRo Frequence Test(s) """

    run_typ()

    # Run corner simulations to get results 
    result = run_corners(CmlRoFreqTb)

    # Or just read them back from file, if we have one
    # result = Result(**pickle.load(open("cmlro.freq.pkl", "rb")))

    # And make some pretty pictures
    plot(result, "CmlRoFreq", "CmlRoFreq.png")
