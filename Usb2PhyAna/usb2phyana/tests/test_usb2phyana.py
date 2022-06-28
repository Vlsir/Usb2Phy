""" 
# USB 2.0 Phy Custom / Analog Tests 
"""

# PyPi Imports
import numpy as np

# HDL & PDK Imports
import sitepdks as _
import s130
from s130 import MosParams
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.sim import Sim

nmos = s130.modules.nmos
nmos_lvt = s130.modules.nmos_lvt
pmos = s130.modules.pmos
pmos_hvt = s130.modules.pmos_hvt

# DUT Imports
from .sim_options import sim_options
from .. import Usb2PhyAna


def test_pdk():
    """ Non-PHY test that we can execute simulations with the installed PDK """

    from hdl21.prefix import µ, m
    from hdl21.primitives import Vdc

    @h.module
    class Tb:
        VSS = h.Port()  # The testbench interface: sole port VSS

        VDD = h.Signal()
        v = Vdc(Vdc.Params(dc=1800 * m))(p=VDD, n=VSS)

        inmos = nmos(MosParams())(d=VDD, g=VDD, s=VSS, b=VSS)
        inmos_lvt = nmos_lvt(MosParams())(d=VDD, g=VDD, s=VSS, b=VSS)
        ipmos = pmos(MosParams())(d=VSS, g=VSS, s=VDD, b=VDD)
        ipmos_hvt = pmos_hvt(MosParams())(d=VSS, g=VSS, s=VDD, b=VDD)

    sim = Sim(tb=Tb, attrs=s130.install.include(Corner.TYP))
    sim.tran(tstop=1 * µ, name="tran1")
    res = sim.run(sim_options)
    print(res)


def test_iv():
    """ I-V Curve Test """
    from hdl21.prefix import m
    from hdl21.sim import LinearSweep
    from hdl21.primitives import Vdc

    # from hdl21.generators import Nmos, MosParams

    @h.module
    class Tb:
        VSS = h.Port()  # The testbench interface: sole port VSS

        # dut = Nmos(MosParams(nser=1, npar=1))(s=VSS, b=VSS)
        dut = nmos_lvt(MosParams(w=1, l=1, m=100))(s=VSS, b=VSS)
        vd = Vdc(Vdc.Params(dc="vds"))(p=dut.d, n=VSS)
        vg = Vdc(Vdc.Params(dc="vgs"))(p=dut.g, n=VSS)

    # Tb = s130.pdk.compile(h.to_proto(Tb))
    # Tb = h.from_proto(Tb)
    # print(Tb)

    sim = Sim(tb=Tb, attrs=s130.install.include(Corner.TYP))
    vgs = sim.param(name="vgs", val=0 * m)
    vds = sim.param(name="vds", val=200 * m)
    sim.dc(var=vgs, sweep=LinearSweep(start=0, stop=2500 * m, step=10 * m), name="dc")
    res = sim.run(sim_options)
    res = res.an[0]  # Get the sole analysis, the DC sweep
    id = np.abs(res.data["xtop.vd:p"])
    gm = np.diff(id) / 10e-3
    gm_over_id = gm / id[:-1]
    print(res)
    print(gm_over_id)
    # np.save("gm_over_id.npy", gm_over_id)


def test_netlisting():
    """ Test netlisting some big-picture Modules """
    import sys

    h.netlist(h.to_proto(Usb2PhyAna), dest=sys.stdout)

