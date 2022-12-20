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
from ...tests.vcode import Vcode
from ...cmlparams import CmlParams
from ..cmlro import CmlRo, CmlIlDco


@h.paramclass
class Pvt:
    """Process, Voltage, and Temperature Parameters"""

    p = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    v = h.Param(dtype=h.Prefixed, desc="Supply Voltage Value (V)", default=1800 * m)
    t = h.Param(dtype=int, desc="Simulation Temperature (C)", default=25)


@h.paramclass
class TbParams:
    """Cml Ro Testbench Parameters"""

    # Required
    cml = h.Param(dtype=CmlParams, desc="Cml Generator Parameters")
    # Optional
    pvt = h.Param(dtype=Pvt, desc="PVT Conditions", default=Pvt())
    code = h.Param(dtype=int, desc="DAC Code", default=16)


@h.generator
def CmlRoFreqTb(params: TbParams) -> h.Module:
    """CmlRo Frequency Testbench"""

    # Create our testbench
    tb = h.sim.tb("CmlRoTb")

    # Generate and drive VDD
    tb.VDD = VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=params.pvt.v, ac=0 * m))(p=VDD, n=tb.VSS)

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

    # DAC Code
    # fctrl = h.Concat(tb.VDD, tb.VSS, tb.VSS, tb.VSS, tb.VSS)
    tb.fctrl = fctrl = h.Signal(width=5)
    tb.vcode = Vcode(code=params.code, width=5, vhi=params.pvt.v)(
        code=fctrl, VSS=tb.VSS
    )

    # Ref Clock Generation
    tb.refclk = h.Signal()
    tb.vrefclk = Vdc(Vdc.Params(dc=0 * m, ac=0 * m))(p=tb.refclk, n=tb.VSS)
    # tb.vrefclk = Vpulse(Vpulse.Params(delay=5 * n, v1=0, v2=params.pvt.v, period=32 * n, rise=100 * p, fall=100 * p, width=16 * n))(p=tb.refclk, n=tb.VSS)

    # Create the DUT
    tb.dut = CmlIlDco(params.cml)(
        stg0=stg0,
        stg1=stg1,
        stg2=stg2,
        stg3=stg3,
        ibias=ibias,
        refclk=tb.refclk,
        fctrl=fctrl,
        VDD=VDD,
        VSS=tb.VSS,
    )

    return tb


def sim_input(tbgen: h.Generator, params: TbParams) -> hs.Sim:
    """CmlRo Frequency Sim"""

    # Create some simulation stimulus
    @hs.sim
    class CmlRoSim:
        # The testbench
        tb = tbgen(params)

        # Our sole analysis: transient, for much longer than we need.
        # But auto-stopping when measurements complete.
        tr = hs.Tran(tstop=500 * n)

        # Measurements
        trise5 = hs.Meas(
            tr, expr="when 'V(xtop.dut.stg0_p)-V(xtop.dut.stg0_n)'=0 rise=5"
        )
        trise15 = hs.Meas(
            tr, expr="when 'V(xtop.dut.stg0_p)-V(xtop.dut.stg0_n)'=0 rise=15"
        )
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
        """
        )

        i = hs.Include(s130.resources / "stdcells.sp")

    # Add the PDK dependencies
    CmlRoSim.add(*s130.install.include(params.pvt.p))

    # # FIXME: handling of multi-directory sims
    # opts = copy(sim_options)
    # opts.rundir = Path(f"./scratch/")

    return CmlRoSim


def run_typ():
    """Run a typical-case sim"""

    print("Running Typical Conditions")
    params = TbParams(pvt=Pvt(), cml=CmlParams(rl=25 * K, cl=10 * f, ib=40 * µ))
    results = sim_input(CmlRoFreqTb, params).run(sim_options)

    print("Typical Conditions:")
    print(results)
