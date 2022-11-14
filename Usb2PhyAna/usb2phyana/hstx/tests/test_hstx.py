""" 
# High-Speed TX Tests
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
from hdl21.primitives import Vdc, Vpulse, Idc, C, R
import s130
import sitepdks as _

from ...tests.sim_options import sim_options
from ...tests.supplyvals import SupplyVals
from ...tests.diffclockgen import DiffClkGen
from ...tests.vcode import Vcode

# DUT Imports
from ..hstx import HsTx, HsTxDriver, CmosPreDriver


@h.paramclass
class Pvt:
    """Process, Voltage, and Temperature Parameters"""

    p = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    v = h.Param(dtype=Corner, desc="Voltage Corner", default=Corner.TYP)
    t = h.Param(dtype=int, desc="Simulation Temperature (C)", default=25)


@h.paramclass
class TbParams:
    pvt = h.Param(dtype=Pvt, desc="PVT Conditions", default=Pvt())
    ib = h.Param(dtype=h.Optional[h.Prefixed], desc="Bias Current", default=100 * µ)


@h.generator
def HsTxDriverTb(params: TbParams) -> h.Module:
    """#  TX Driver Testbench"""

    # Create our testbench
    tb = h.sim.tb(name="HsTxDriverTb")

    # Set up its supplies
    supplyvals = SupplyVals.corner(params.pvt.v)
    tb.VDD33 = VDD33 = h.Signal()
    tb.VDD18 = VDD18 = h.Signal()
    tb.vvdd18 = Vdc(dc=supplyvals.VDD18, ac=0 * m)(p=VDD18, n=tb.VSS)
    tb.vvdd33 = Vdc(dc=supplyvals.VDDA33, ac=0 * m)(p=VDD33, n=tb.VSS)

    # Pads
    tb.pads = pads = h.Diff()
    # Termination & Loading
    tb.rt = h.Pair(R(r=22.5))(p=pads, n=tb.VSS)
    tb.cl = h.Pair(C(c=500 * f))(p=pads, n=tb.VSS)

    # Bias
    tb.pbias = pbias = h.Signal()
    tb.ii = Idc(Idc.Params(dc=params.ib))(p=pbias, n=tb.VSS)

    # Data Generation
    tb.data_p = h.Signal()
    tb.data_n = h.Signal()
    data_gen_params = DiffClkGen.Params(
        period=4167 * p, delay=125 * p, vc=900 * m, vd=1800 * m, trf=100 * p
    )
    tb.datagen = DiffClkGen(data_gen_params)(
        ck=h.AnonymousBundle(p=tb.data_p, n=tb.data_n), VSS=tb.VSS
    )

    ## PreDrivers
    tb.dp_b, tb.dn_b, tb.shunt_b = h.Signals(3)
    tb.predrivers = 3 * CmosPreDriver(h.Default)(
        datab_1v8=h.Concat(tb.data_p, tb.data_n, tb.VSS),
        en_3v3=tb.VDD33,
        out=h.Concat(tb.dp_b, tb.dn_b, tb.shunt_b),
        VDD18=VDD18,
        VDD33=VDD33,
        VSS=tb.VSS,
    )

    ## High-Speed TX DUT
    tb.dut = HsTxDriver(h.Default)(
        pads=pads,
        # hstx_enb_3v3=tb.VSS,
        dp_b=tb.dp_b,
        dn_b=tb.dn_b,
        shunt_b=tb.VDD18,
        pbias=pbias,
        VDD18=VDD18,
        VDD33=VDD33,
        VSS=tb.VSS,
    )

    return tb


def test_hstx_driver():
    """High Speed TX Tests"""

    params = TbParams(pvt=Pvt(p=Corner.SLOW, v=Corner.SLOW, t=-25))

    # Create some simulation stimulus
    @hs.sim
    class HsTxDriverSim:
        # The testbench
        tb = HsTxDriverTb(params)

        tr = hs.Tran(tstop=50 * n)
        # op = hs.Op()

    # Add the PDK dependencies
    HsTxDriverSim.add(*s130.install.include(params.pvt.p))

    results = HsTxDriverSim.run(sim_options)
    print(results)


def test_elaboration():
    h.elaborate(HsTx())


def test_netlist():
    import sys

    h.netlist(HsTx(), sys.stdout)
