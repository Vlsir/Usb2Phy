""" 
USB 2.0 Phy Custom / Analog Tests 
"""

# Std-Lib Imports
from pathlib import Path

import sitepdks as _
import s130
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.sim import Sim
from vlsirtools.spice import SimOptions, SupportedSimulators, ResultFormat

# DUT Imports
from usb2phyana import Usb2PhyAna
from usb2phyana.rotator import OneHotRotator

# Widely re-used `SimOptions`
sim_options = SimOptions(
    rundir=Path("./scratch"),
    fmt=ResultFormat.SIM_DATA,
    simulator=SupportedSimulators.SPECTRE,
)


def test_pdk():
    """ Non-PHY test that we can execute simulations with the installed PDK """

    from hdl21.prefix import µ, m
    from hdl21.primitives import Vdc

    @h.module
    class Tb:
        VSS = h.Port()  # The testbench interface: sole port VSS

        VDD = h.Signal()
        v = Vdc(Vdc.Params(dc=1800 * m))(p=VDD, n=VSS)

        nmos = s130.modules.nmos(s130.MosParams())(d=VDD, g=VDD, s=VSS, b=VSS)
        nmos_lvt = s130.modules.nmos_lvt(s130.MosParams())(d=VDD, g=VDD, s=VSS, b=VSS)
        pmos = s130.modules.pmos(s130.MosParams())(d=VSS, g=VSS, s=VDD, b=VDD)
        pmos_hvt = s130.modules.pmos_hvt(s130.MosParams())(d=VSS, g=VSS, s=VDD, b=VDD)

    sim = Sim(tb=Tb, attrs=s130.install.include(Corner.TYP))
    sim.tran(tstop=1 * µ, name="tran1")
    res = sim.run(sim_options)
    print(res)


def test_onehot_rotator():
    """ Simulate the `OneHotRotator` """

    def rotator_tb() -> h.Module:
        from hdl21.prefix import m, n, p, f
        from hdl21.primitives import Vdc, Vpulse, Cap

        # "Parameter" Width
        width = 16

        tb = h.sim.tb("OneHotRotatorTb")
        tb.VDD = h.Signal()
        tb.vvdd = Vdc(Vdc.Params(dc=1800 * m))(p=tb.VDD, n=tb.VSS)

        # Instantiate the rotator DUT
        tb.dut = OneHotRotator(width=width)(VDD=tb.VDD, VSS=tb.VSS)

        tb.cloads = width * Cap(Cap.Params(c=1 * f))(p=tb.dut.out, n=tb.VSS)

        tb.vsclk = Vpulse(
            Vpulse.Params(
                delay=0,
                v1=0,
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
                v1=0,
                v2=1800 * m,
                period=2,
                rise=1 * p,
                fall=1 * p,
                width=1,
            )
        )(p=tb.dut.rstn, n=tb.VSS)

        return tb

    def rotator_sim() -> h.sim.Sim:
        from hdl21.prefix import n

        sim = h.sim.Sim(tb=rotator_tb(), attrs=s130.install.include(Corner.TYP))
        sim.tran(tstop=64 * n, name="THE_TRAN_DUH")
        return sim

    sim = rotator_sim()
    sim.include("scs130lp.sp")  # FIXME! relies on this netlist of logic cells
    results = sim.run(sim_options)

    print(results)


def test_netlisting():
    """ Test netlisting some big-picture Modules """
    import sys

    # h.netlist(h.to_proto(Serdes(SerdesParams())), dest=sys.stdout)
    # h.netlist(h.to_proto(SerdesTxLane), dest=sys.stdout)
    # h.netlist(h.to_proto(SerdesRxLane), dest=sys.stdout)
    # h.netlist(h.to_proto(OneHotEncoder(width=10)), dest=sys.stdout)
    h.netlist(h.to_proto(Usb2PhyAna), dest=sys.stdout)
    h.netlist(h.to_proto(OneHotRotator(width=8)), dest=sys.stdout)
    # h.netlist(h.to_proto(PhaseInterp()), dest=sys.stdout)
