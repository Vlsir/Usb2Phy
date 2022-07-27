""" 
# High-Speed RX Tests
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
from hdl21.prefix import m, µ, f, n, T, p, PICO
from hdl21.primitives import Vdc, Vpulse, Idc, C
import s130
import sitepdks as _

from ...tests.sim_options import sim_options
from ...tests.supplyvals import SupplyVals
from ...tests.diffclockgen import DiffClkGen
from ...tests.vcode import Vcode

# DUT Imports
from ..hsrx import HsRx
from ...ilo import IloParams


@h.paramclass
class Pvt:
    """Process, Voltage, and Temperature Parameters"""

    p = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    v = h.Param(dtype=Corner, desc="Voltage Corner", default=Corner.TYP)
    t = h.Param(dtype=int, desc="Simulation Temperature (C)", default=25)


@h.paramclass
class TbParams:
    pvt = h.Param(dtype=Pvt, desc="PVT Conditions", default=Pvt())
    ilo = h.Param(
        dtype=IloParams, desc="Hsrx Generator Parameters", default=IloParams()
    )
    ib = h.Param(dtype=h.ScalarOption, desc="Bias Current", default=120 * µ)
    code = h.Param(dtype=int, desc="Fctrl Dac Code", default=16)


@h.generator
def HsRxTb(params: TbParams) -> h.Module:
    """# High Speed RX Testbench Generator"""

    # Create our testbench
    tb = h.sim.tb(name="HsRxTb")

    # Set up its supplies
    supplyvals = SupplyVals.corner(params.pvt.v)
    tb.VDD33 = VDD33 = h.Signal()
    tb.VDD18 = VDD18 = h.Signal()
    tb.vvdd18 = Vdc(dc=supplyvals.VDD18)(p=VDD18, n=tb.VSS)
    tb.vvdd33 = Vdc(dc=supplyvals.VDDA33)(p=VDD33, n=tb.VSS)

    # Pad data generator
    tb.pads = pads = h.Diff()
    data_gen_params = DiffClkGen.Params(
        period=4167 * p, delay=125 * p, vc=200 * m, vd=400 * m, trf=800 * p
    )
    tb.ckgen = DiffClkGen(data_gen_params)(ck=pads, VSS=tb.VSS)

    # Frequency DAC Code
    tb.fctrl = fctrl = h.Signal(width=5)
    tb.vcode = Vcode(code=params.code, width=5, vhi=supplyvals.VDD18)(
        code=fctrl, VSS=tb.VSS
    )

    # Primary Clock & Data Outputs
    tb.sck = sck = h.Signal()
    tb.sdata = sdata = h.Signal()

    # Bias
    tb.pbias_cdr_120u = pbias_cdr_120u = h.Signal()
    tb.ii_cdr = Idc(Idc.Params(dc=120 * µ))(p=pbias_cdr_120u, n=tb.VSS)
    tb.pbias_preamp_200u = pbias_preamp_200u = h.Signal()
    tb.ii_preamp = Idc(Idc.Params(dc=200 * µ))(p=pbias_preamp_200u, n=tb.VSS)

    ## High-Speed RX DUT
    tb.dut = HsRx(h.Default)(
        pads=pads,
        sck=sck,
        sdata=sdata,
        fctrl=fctrl,
        cdr_en=VDD18,
        pbias_cdr_120u=pbias_cdr_120u,
        pbias_preamp_200u=pbias_preamp_200u,
        VDD18=VDD18,
        VDD33=VDD33,
        VSS=tb.VSS,
    )

    return tb


def test_hsrx():
    """High Speed RX Tests"""

    params = TbParams()

    # Create some simulation stimulus
    @hs.sim
    class HsrxSim:
        # The testbench
        tb = HsRxTb(params)

        # Our sole analysis: transient
        tr = hs.Tran(tstop=50 * n)

        # The stuff we can't first-class represent, and need to stick in a literal.
        l = hs.Literal(
            f"""
            simulator lang=spice
            .ic xtop.stg0_p 900m
            .ic xtop.stg0_n 0
            .temp {params.pvt.t}
            simulator lang=spectre
        """
        )
        i = hs.Include(
            "/tools/B/dan_fritchman/dev/VlsirWorkspace/Usb2Phy/Usb2PhyAna/resources/scs130lp.sp"
        )

    # Add the PDK dependencies
    HsrxSim.add(*s130.install.include(params.pvt.p))

    results = HsrxSim.run(sim_options)
    print(results)
