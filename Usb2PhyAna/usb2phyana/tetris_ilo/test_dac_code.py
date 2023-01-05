from typing import List, Optional
from dataclasses import asdict, replace
from copy import copy

from pydantic.dataclasses import dataclass
import numpy as np
import matplotlib.pyplot as plt

# Hdl Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.pdk import Corner
from hdl21.prefix import µ, m, n, PICO

# PDK Imports
import s130
import sitepdks as _

# Local Imports
from ..tests.sim_options import sim_options
from ..tests.sim_test_mode import SimTest
from ..tests.supplyvals import SupplyVals
from ..tests.vcode import Vcode
from ..pvt import Pvt, Project
from .tetris_ilo import Ilo, IloParams, OctalClock

# Module-wide reused parameters
result_pickle_file = "scratch/cmosilo.dac_code.pkl"
codes = list(range(0, 32))


@h.paramclass
class TbParams:
    pvt = h.Param(dtype=Pvt, desc="PVT Conditions", default=Pvt())
    ilo = h.Param(dtype=IloParams, desc="Ilo Generator Parameters", default=IloParams())
    ib = h.Param(dtype=h.Scalar, desc="Bias Current", default=384 * µ)
    code = h.Param(dtype=int, desc="Fctrl Dac Code", default=16)


@h.generator
def IloWrapper(params: IloParams) -> h.Module:
    m = h.Module(name="IloWrapper")

    # Wrap up the octal-clock signals at this level
    m.cko = OctalClock()

    # IO
    m.VDDA33, m.VDD18, m.VSS = h.Ports(3)
    m.inj = h.Input(desc="Injection Input")
    m.pbias = h.Input()
    m.fctrl = h.Input(width=5)
    m.cko = OctalClock()

    # Create the Ilo DUT
    m.dut = Ilo(params)(
        fctrl=m.fctrl,
        inj=m.inj,
        pbias=m.pbias,
        cko=m.cko,
        SUPPLIES=h.bundlize(
            VDD33=m.VDDA33,
            VDD18=m.VDD18,
            VSS=m.VSS,
        ),
    )
    return m


@h.generator
def IloFreqTb(params: TbParams) -> h.Module:
    """Ilo Frequency Testbench"""

    # Create our testbench
    tb = hs.tb("IloFreqTb")

    # Generate and drive VDD
    supplyvals = SupplyVals.corner(params.pvt.v)
    tb.VDDA33 = VDDA33 = h.Signal()
    tb.VDD18 = VDD18 = h.Signal()
    tb.vvdd18 = h.Vdc(dc=supplyvals.VDD18)(p=VDD18, n=tb.VSS)
    tb.vvdd33 = h.Vdc(dc=supplyvals.VDDA33)(p=VDDA33, n=tb.VSS)

    # Bias Generation
    tb.pbias = pbias = h.Signal()
    # Pmos Side Bias
    tb.ii = h.Idc(dc=1 * params.ib)(p=pbias, n=tb.VSS)

    # Frequency Control Dac Code
    tb.fctrl = fctrl = h.Signal(width=5)
    tb.vfctrl = Vcode(code=params.code, width=5, vhi=supplyvals.VDD18)(
        code=fctrl, VSS=tb.VSS
    )

    # Create the injection-pulse *Signal*, but not its driver
    tb.inj = h.Signal()

    # Create the injection-pulse source, which in this bench serves entirely as a kick-start
    tb.vinj = h.Vpulse(
        v1=0 * m,
        v2=1800 * m,
        period=1001 * m,  # "Infinite" period
        rise=10 * PICO,
        fall=10 * PICO,
        width=1 * n,
        delay=2 * n,
    )(p=tb.inj, n=tb.VSS)

    # Instantiate the (wrapped) ILO
    tb.wrapper = IloWrapper(params.ilo)(
        fctrl=tb.fctrl,
        inj=tb.inj,
        pbias=tb.pbias,
        VDDA33=tb.VDDA33,
        VDD18=tb.VDD18,
        VSS=tb.VSS,
    )

    return tb


def sim_input(params: TbParams) -> hs.Sim:
    """Ilo Frequency Sim"""

    tb_ = IloFreqTb(params)
    s130.compile(tb_)

    # Create some simulation stimulus
    @hs.sim
    class IloSim:
        # The testbench
        tb = tb_

        # Our sole analysis: transient, for much longer than we need.
        # But auto-stopping when measurements complete.
        tr = hs.Tran(tstop=500 * n)
        op = hs.Op()

        # Measurements
        trise5 = hs.Meas(
            tr,
            expr="when 'V(xtop.wrapper.cko_stg0_p)-V(xtop.wrapper.cko_stg0_n)'=0 rise=25",
        )
        trise15 = hs.Meas(
            tr,
            expr="when 'V(xtop.wrapper.cko_stg0_p)-V(xtop.wrapper.cko_stg0_n)'=0 rise=35",
        )
        tperiod = hs.Meas(tr, expr="param='(trise15-trise5)/10'")
        idd = hs.Meas(tr, expr="avg I(xtop.vvdd18) from=trise5 to=trise15")
        idac = hs.Meas(tr, expr="avg I(xtop.dut.visns) from=trise5 to=trise15")
        vring = hs.Meas(tr, expr="avg V(xtop.dut.ring_top) from=trise5 to=trise15")

        # The stuff we can't first-class represent, and need to stick in a literal.
        l = hs.Literal(
            f"""
            simulator lang=spice
            .temp {Project.temper(params.pvt.t)}
            .option autostop
            simulator lang=spectre
        """
        )

        i = hs.Include(s130.resources / "stdcells.sp")

    # Add the PDK dependencies
    IloSim.add(*s130.install.include(params.pvt.p))

    return IloSim


def idd(results: hs.SimResult) -> float:
    return results.an[0].measurements["idd"]


def tperiod(results: hs.SimResult) -> float:
    return results.an[0].measurements["tperiod"]


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


def run_corners() -> Result:
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
        cond_results = codesweep(pvt)
        result.cond_results.append(cond_results)

    pickle.dump(asdict(result), open(result_pickle_file, "wb"))
    return result


def codesweep(pvt: Pvt) -> ConditionResult:
    """Run `sim` on `tbgen`, across codes, at conditions `pvt`."""

    # Create the simulation inputs
    params = [TbParams(pvt=pvt, code=code) for code in codes]
    sims = [sim_input(params=p) for p in params]

    # Run sims
    opts = replace(sim_options, rundir=None)
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
    freqs = np.array([r.freq for r in cond_results.summaries])

    # And plot the results
    ax.plot(codes, freqs / 1e6, label=str(cond))


def idd(results: hs.SimResult) -> float:
    return results.an[0].measurements["idd"]


def tperiod(results: hs.SimResult) -> float:
    return results.an[0].measurements["tperiod"]


class TestIloDacCode(SimTest):
    """Cmos Ilo Dac Code vs Frequence Test(s)"""

    tbgen = IloFreqTb

    def min(self):
        """Run a typical-case, mid-code sim"""
        opts = replace(sim_options, rundir="./scratch")
        sim_result = sim_input(params=TbParams()).run(opts)
        summary = SingleSimSummary.build(sim_result)
        # print(summary)

    def typ(self):
        """Sweep DAC codes at typical PVT conditions"""
        results = codesweep(pvt=Pvt())
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
