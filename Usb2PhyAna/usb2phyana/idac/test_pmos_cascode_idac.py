""" 
# Pmos Idac Test(s)
"""

import pickle, io
from typing import List
from dataclasses import asdict
from copy import copy

from pydantic.dataclasses import dataclass
import numpy as np
import matplotlib.pyplot as plt

# Hdl Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.pdk import Corner
from hdl21.prefix import µ, m
from hdl21.primitives import Vdc, Idc

# PDK Imports
import s130
import sitepdks as _

# Local Imports
from ..tests.supplyvals import SupplyVals
from ..tests.sim_options import sim_options
from ..tests.vcode import Vcode
from .pmos_cascode_idac import PmosIdac


result_pickle_file = "scratch/pmos_cascode_idac.codesweep.pkl"


@h.paramclass
class Pvt:
    """Process, Voltage, and Temperature Parameters"""

    p = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    v = h.Param(dtype=Corner, desc="Voltage Corner", default=Corner.TYP)
    t = h.Param(dtype=int, desc="Simulation Temperature (C)", default=25)


@h.paramclass
class TbParams:
    """Cml Ro Testbench Parameters"""

    # Optional
    ib = h.Param(dtype=h.Prefixed, desc="Bias Current Value (A)", default=100 * µ)
    pvt = h.Param(dtype=Pvt, desc="PVT Conditions", default=Pvt())
    code = h.Param(dtype=int, desc="DAC Code", default=16)


@h.generator
def IdacSweepTb(params: TbParams) -> h.Module:
    """Idac Sweep Testbench"""

    # Create our testbench
    tb = h.sim.tb("IdacSweepTb")

    # Generate and drive VDD
    supplyvals = SupplyVals.corner(params.pvt.v)
    tb.VDDA33 = VDDA33 = h.Signal()
    tb.VDD18 = VDD18 = h.Signal()
    tb.vvdd18 = Vdc(dc=supplyvals.VDD18)(p=VDD18, n=tb.VSS)
    tb.vvdd33 = Vdc(dc=supplyvals.VDDA33)(p=VDDA33, n=tb.VSS)

    # Bias Generation
    tb.ibias = ibias = h.Signal()
    # Pmos Side Bias
    tb.ii = Idc(Idc.Params(dc=params.ib))(p=ibias, n=tb.VSS)

    # DAC Code
    tb.code = code = h.Signal(width=5)
    tb.vcode = Vcode(code=params.code, width=5, vhi=supplyvals.VDD18)(
        code=code, VSS=tb.VSS
    )

    # Current Output, into a load equal to that in the CML RO
    # tb.out, tb.pbias = out, pbias = h.Signals(2)
    # tb.pload = Pbias(g=pbias, d=pbias, s=VDD, b=VDD)
    tb.out = out = h.Signal()
    tb.vout = Vdc(dc=0 * m)(p=out, n=tb.VSS)

    # Create the DUT
    tb.dut = PmosIdac()(
        code=code, out=out, ibias=ibias, VDDA33=VDDA33, VDD18=VDD18, VSS=tb.VSS
    )

    return tb


def sim_input(tbgen: h.Generator, params: TbParams) -> hs.Sim:
    """Idac Code Sweep Sim"""

    # Create some simulation stimulus
    @hs.sim
    class IdacCodeSweepSim:
        # The testbench
        tb = tbgen(params)

        # Our sole analysis: DC operating point
        op = hs.Op()

        # The stuff we can't first-class represent, and need to stick in a literal.
        l = hs.Literal(
            f"""
            simulator lang=spice
            .temp {params.pvt.t}
            simulator lang=spectre
        """
        )

        i = hs.Include(s130.resources / "stdcells.sp")

    # Add the PDK dependencies
    IdacCodeSweepSim.add(*s130.install.include(params.pvt.p))

    return IdacCodeSweepSim


def iout(result: hs.SimResult) -> float:
    return result.an[0].data["xtop.vout:p"]


def codesweep(tbgen: h.Generator, pvt: Pvt) -> List[hs.SimResult]:
    """Run `sim` on `tbgen`, across codes, at conditions `pvt`."""

    # FIXME: share this stuff with `Result`
    codes = range(0, 32)
    opts = copy(sim_options)
    opts.rundir = None

    params = [TbParams(pvt=pvt, code=code) for code in codes]

    # Create the simulation inputs
    sims = [sim_input(tbgen=tbgen, params=p) for p in params]

    # Run sims
    return h.sim.run(sims, opts)


@dataclass
class Result:
    """Result type for the PVT-parameterized DAC code sweep"""

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
        for t in [-25, 25, 75]
    ]
    result = Result(conditions=conditions, codes=list(range(0, 32)), results=[])

    # Run conditions one at a time, parallelizing across codes
    for pvt in conditions:
        print(f"Simulating {pvt}")
        condition_results = codesweep(tbgen=tbgen, pvt=pvt)
        result.results.append(condition_results)

    pickle.dump(asdict(result), open(result_pickle_file, "wb"))

    return result


def run_one() -> hs.SimResult:
    """Run a typical-case, mid-code sim"""

    print("Running Typical Conditions")
    params = TbParams(pvt=Pvt(), code=16)
    results = sim_input(IdacSweepTb, params).run(sim_options)

    print("Typical Condition Results:")
    print(results)


def run_typ() -> List[hs.SimResult]:
    """Run a typical-case code-sweep"""

    print("Running Typical Condition Code Sweep")
    results = codesweep(IdacSweepTb, Pvt())

    print("Typical Condition Results:")
    print(results)


def plot(result: Result, title: str, fname: str):
    """Plot code sweeps, parameterized by PVT"""

    fig, ax = plt.subplots()
    codes = np.array(result.codes)

    for (cond, cond_results) in zip(result.conditions, result.results):
        iouts = 1e6 * np.abs(np.array([iout(r) for r in cond_results]))
        label = f"{str(cond.p), str(cond.v), str(cond.t)}"
        print(label, iouts[15])
        ax.plot(codes, iouts, label=label)

    # Set up all the other data on our plot
    ax.set_title(title)
    ax.set_xlabel("Dac Code")
    ax.set_ylabel("Dac Output Current (µA)")
    ax.legend()

    # And save it to file
    fig.savefig(fname)


def run_and_plot_corners():
    # Run corner simulations to get results
    result = run_corners(IdacSweepTb)

    # Or just read them back from file, if we have one
    result = Result(**pickle.load(open(result_pickle_file, "rb")))

    # And make some pretty pictures
    plot(result, "IdacCodeSweep", "scratch/IdacCodeSweep.png")


from ..tests.sim_test_mode import SimTestMode


def test_idac_code_sweep(simtestmode: SimTestMode):
    """Test DAC Code Sweep"""

    if simtestmode == SimTestMode.NETLIST:
        params = TbParams(pvt=Pvt(), code=16)
        h.netlist(IdacSweepTb(params), dest=io.StringIO())
    elif simtestmode == SimTestMode.MIN:
        run_one()
    elif simtestmode == SimTestMode.TYP:
        codesweep(pvt=Pvt())
    else:
        run_and_plot_corners()
