""" 
# OneHotRotator Tests
"""

import io

# HDL & PDK Imports
import sitepdks as _
import s130
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.prefix import m, n, p, f
from hdl21.primitives import Vdc, Vpulse, Cap

# DUT Imports
from ..tests.sim_options import sim_options
from .rotator import OneHotRotator


def rotator_tb() -> h.Module:
    """Create the testbench for `OneHotRotator`"""

    # "Parameter" Width
    width = 16

    tb = h.sim.tb("OneHotRotatorTb")
    tb.VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=1800 * m, ac=0 * m))(p=tb.VDD, n=tb.VSS)

    # Instantiate the rotator DUT
    tb.dut = OneHotRotator(width=width)(VDD=tb.VDD, VSS=tb.VSS)

    tb.cloads = width * Cap(Cap.Params(c=1 * f))(p=tb.dut.out, n=tb.VSS)

    tb.vsclk = Vpulse(
        Vpulse.Params(
            delay=0 * m,
            v1=0 * m,
            v2=1800 * m,
            period=2 * n,
            rise=1 * p,
            fall=1 * p,
            width=1 * n,
        )
    )(p=tb.dut.sclk, n=tb.VSS)
    tb.vrstn = Vpulse(
        Vpulse.Params(
            delay=9500 * p,
            v1=0 * m,
            v2=1800 * m,
            period=2000 * m,  # "Infinite" 2s period
            rise=1 * p,
            fall=1 * p,
            width=1000 * m,
        )
    )(p=tb.dut.rstn, n=tb.VSS)

    return tb


from ..tests.sim_test_mode import SimTestMode


def test_onehot_rotator(simtestmode: SimTestMode):
    if simtestmode == SimTestMode.NETLIST:
        h.netlist(rotator_tb(), dest=io.StringIO())
    else:
        sim_onehot_rotator()


def sim_onehot_rotator():
    """Simulate the `OneHotRotator`"""
    from hdl21.prefix import n

    sim = h.sim.Sim(tb=rotator_tb(), attrs=s130.install.include(Corner.TYP))
    sim.tran(tstop=64 * n, name="THE_TRAN_DUH")
    
    sim.include(s130.resources / "stdcells.sp")
    results = sim.run(sim_options)

    print(results)
