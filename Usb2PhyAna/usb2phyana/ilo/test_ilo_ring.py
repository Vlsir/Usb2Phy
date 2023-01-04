""" 
# ILO Tests 
"""

from typing import List
from dataclasses import replace

from pandas import DataFrame
from pydantic.dataclasses import dataclass

# Hdl Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.prefix import m, n, PICO

# PDK Imports
import s130
import sitepdks as _

# Local Imports
from ..tests.sim_options import sim_options
from ..tests.sim_test_mode import SimTest
from ..tests.supplyvals import SupplyVals
from .tb import Pvt
from .ilo import IloRing, IloParams, OctalClock


@h.paramclass
class TbParams:
    vvdd = h.Param(dtype=h.Scalar, desc="VDD Voltage (V)", default=1800 * m)
    pvt = h.Param(dtype=Pvt, desc="PVT Conditions", default=Pvt())
    ilo = h.Param(dtype=IloParams, desc="Ilo Generator Parameters", default=IloParams())


@h.generator
def IloRingFreqTb(params: TbParams) -> h.Module:
    """Ilo Ring Frequency Testbench"""

    # Create our testbench
    tb = h.sim.tb("IloRingFreqTb")

    # Generate and drive VDD
    tb.VDD18 = VDD18 = h.Signal()
    tb.vvdd18 = h.Vdc(dc=params.vvdd)(p=VDD18, n=tb.VSS)

    # Create the test-bench level delay stage signals
    tb.cko = OctalClock()

    # Create the injection-pulse source, which in this bench serves entirely as a kick-start
    tb.inj = h.Signal()
    tb.vinj = h.Vpulse(
        v1=1800 * m,
        v2=0 * m,
        period=1001 * m,  # "Infinite" period
        rise=10 * PICO,
        fall=10 * PICO,
        width=1000 * m,
        delay=10 * PICO,
    )(p=tb.inj, n=tb.VSS)

    # Create the Ilo DUT
    tb.dut = IloRing(params.ilo)(
        inj=tb.inj,
        cko=tb.cko,
        VDD=tb.VDD18,
        VSS=tb.VSS,
    )

    return tb


def sim_input(params: TbParams) -> hs.Sim:
    """Ilo Frequency Sim"""

    tb_ = IloRingFreqTb(params)
    s130.compile(tb_)

    # Create some simulation stimulus
    @hs.sim
    class IloSim:
        # The testbench
        tb = tb_

        # Our sole analysis: transient, for much longer than we need.
        # But auto-stopping when measurements complete.
        tr = hs.Tran(tstop=500 * n)

        # Measurements
        trise5 = hs.Meas(
            tr, expr="when 'V(xtop.cko_stg0_p)-V(xtop.cko_stg0_n)'=0 rise=5"
        )
        trise15 = hs.Meas(
            tr, expr="when 'V(xtop.cko_stg0_p)-V(xtop.cko_stg0_n)'=0 rise=15"
        )
        tperiod = hs.Meas(tr, expr="param='(trise15-trise5)/10'")
        idd = hs.Meas(tr, expr="avg I(xtop.vvdd18) from=trise5 to=trise15")

        # The stuff we can't first-class represent, and need to stick in a literal.
        l = hs.Literal(
            f"""
            simulator lang=spice
            .temp {params.pvt.t}
            .option autostop
            simulator lang=spectre
        """
        )

        i = hs.Include(s130.resources / "stdcells.sp")

    # Add the PDK dependencies
    IloSim.add(*s130.install.include(params.pvt.p))

    return IloSim


@dataclass
class SingleSimSummary:
    freq: float
    idd: float

    @classmethod
    def build(cls, sim_result: hs.SimResult) -> "SingleSimSummary":
        freq = 1 / tperiod(sim_result)
        idd_ = abs(1e6 * idd(sim_result))
        return cls(freq, idd_)


def idd(results: hs.SimResult) -> float:
    return results.an[0].measurements["idd"]


def tperiod(results: hs.SimResult) -> float:
    return results.an[0].measurements["tperiod"]


@dataclass
class ConditionResult:
    # Results at a single PVT condition
    cond: Pvt
    vdds: List[h.Scalar]
    summaries: List[SingleSimSummary]

    def table(self) -> DataFrame:
        return DataFrame(
            dict(
                vdd=[1000 * float(v) for v in self.vdds],
                freq=[s.freq for s in self.summaries],
                idd=[s.idd for s in self.summaries],
            )
        )


def vddsweep(pvt: Pvt) -> ConditionResult:
    """Run `sim` on `tbgen`, across vdd, at conditions `pvt`."""

    opts = replace(sim_options, rundir=None)
    vdds = [x * m for x in range(500, 2001, 100)]
    params = [TbParams(pvt=pvt, vvdd=v) for v in vdds]

    # Create the simulation inputs
    sims = [sim_input(params=p) for p in params]

    # Run sims
    sim_results = h.sim.run(sims, opts)

    # And collate them into a `ConditionResult`
    return ConditionResult(
        cond=pvt,
        vdds=vdds,
        summaries=[SingleSimSummary.build(s) for s in sim_results],
    )


class TestIloRingFreqVsVdd(SimTest):
    """Ilo Ring - Frequency vs Vdd Test(s)"""

    tbgen = IloRingFreqTb

    def min(self):
        """Run a typical-case, typical-supply sim"""

        opts = replace(sim_options, rundir="./scratch")
        sim_result = sim_input(params=TbParams()).run(opts)
        summary = SingleSimSummary.build(sim_result)
        print("Typical Condition Results:")
        print(summary)

    def typ(self):
        """Sweep VDD at typical PVT conditions"""
        results = vddsweep(pvt=Pvt())
        print(results.table())

    def max(self):
        """Sweep VDD across PVT conditions"""
        raise NotImplementedError  # FIXME!
