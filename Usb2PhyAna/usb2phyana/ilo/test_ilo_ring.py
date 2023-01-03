""" 
# ILO Tests 
"""

import pickle, io
from typing import List
from dataclasses import asdict, replace
from copy import copy

from pydantic.dataclasses import dataclass
import numpy as np
import matplotlib.pyplot as plt

# Hdl Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.pdk import Corner
from hdl21.prefix import m, µ, n, PICO

# PDK Imports
import s130
import sitepdks as _

# Local Imports
from ..tests.sim_options import sim_options
from ..tests.sim_test_mode import SimTest
from ..tests.supplyvals import SupplyVals
from .tb import Pvt, TbParams, sim_input
from .ilo import IloRing, IloParams, OctalClock


@h.generator
def IloRingFreqTb(params: TbParams) -> h.Module:
    """Ilo Ring Frequency Testbench"""

    # Create our testbench

    # Create our testbench
    tb = h.sim.tb("IloRingFreqTb")

    # Generate and drive VDD
    supplyvals = SupplyVals.corner(params.pvt.v)
    tb.VDDA33 = VDDA33 = h.Signal()
    tb.VDD18 = VDD18 = h.Signal()
    tb.vvdd18 = h.Vdc(dc=supplyvals.VDD18)(p=VDD18, n=tb.VSS)
    tb.vvdd33 = h.Vdc(dc=supplyvals.VDDA33)(p=VDDA33, n=tb.VSS)

    # Create the test-bench level delay stage signals
    tb.cko = OctalClock()

    # Create the injection-pulse *Signal*, but not its driver
    tb.inj = h.Signal()

    tb.stg0 = h.Diff()
    tb.stg1 = h.Diff()
    tb.stg2 = h.Diff()
    tb.stg3 = h.Diff()

    tb.cko = OctalClock()

    # Create the Ilo DUT
    tb.dut = IloRing(params.ilo)(
        inj=tb.inj,
        cko=tb.cko,
        # stg0=tb.stg0,
        # stg1=tb.stg1,
        # stg2=tb.stg2,
        # stg3=tb.stg3,
        VDD=tb.VDD18,
        VSS=tb.VSS,
    )

    # Create the injection-pulse source, which in this bench serves entirely as a kick-start
    tb.vinj = h.Vpulse(
        v1=1800 * m,
        v2=0 * m,
        period=1001 * m,  # "Infinite" period
        rise=10 * PICO,
        fall=10 * PICO,
        width=1000 * m,
        delay=10 * PICO,
    )(p=tb.inj, n=tb.VSS)

    return tb


def sim_input(tbgen: h.Generator, params: TbParams) -> hs.Sim:
    """Ilo Frequency Sim"""

    tb_ = tbgen(params)
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
        idd = hs.Meas(tr, expr="avg I(xtop.vvdd) from=trise5 to=trise15")

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


class TestIloRingFreqVsVdd(SimTest):
    """Ilo Ring - Frequency vs Vdd Test(s)"""

    tbgen = IloRingFreqTb

    def min(self):
        sim_input(tbgen=IloRingFreqTb, params=TbParams()).run(
            replace(sim_options, rundir="./scratch")
        )
