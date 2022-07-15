
from dataclasses import dataclass 

# PyPi Imports
import numpy as np
import matplotlib.pyplot as plt 

# HDL & PDK Imports
import sitepdks as _
import s130
from s130 import MosParams, IoMosParams

import hdl21 as h
import hdl21.sim as hs
from hdl21.pdk import Corner
from hdl21.sim import Sim, LogSweep, LinearSweep
from hdl21.prefix import e, m, µ
from hdl21.primitives import MosType, Vdc

# Local Imports
from .sim_options import sim_options


nmos = s130.modules.nmos
nmos_lvt = s130.modules.nmos_lvt
pmos = s130.modules.pmos
pmos_hvt = s130.modules.pmos_hvt
pmos_v5 = s130.modules.pmos_v5


def test_pdk():
    """ Non-PHY test that we can execute simulations with the installed PDK """

    @h.module
    class Tb:
        VSS = h.Port()  # The testbench interface: sole port VSS

        VDD = h.Signal()
        v = Vdc(Vdc.Params(dc=1800 * m))(p=VDD, n=VSS)

        inmos = nmos(MosParams())(d=VDD, g=VDD, s=VSS, b=VSS)
        inmos_lvt = nmos_lvt(MosParams())(d=VDD, g=VDD, s=VSS, b=VSS)
        ipmos = pmos(MosParams())(d=VSS, g=VSS, s=VDD, b=VDD)
        ipmos_hvt = pmos_hvt(MosParams())(d=VSS, g=VSS, s=VDD, b=VDD)
        ipmos_v5 = pmos_v5(IoMosParams())(d=VSS, g=VSS, s=VDD, b=VDD)

    sim = Sim(tb=Tb, attrs=s130.install.include(Corner.TYP))
    sim.tran(tstop=1 * µ, name="tran1")
    res = sim.run(sim_options)
    print(res)


@dataclass 
class MosDut:
    """ Dut info for the IV Curve Test """
    dut: h.Instantiable 
    mostype: MosType


def test_iv():
    """ I-V Curve Test """
    
    duts = [
        MosDut(nmos(MosParams()), MosType.NMOS),
        MosDut(nmos_lvt(MosParams()), MosType.NMOS),
        MosDut(pmos(MosParams()), MosType.PMOS),
        MosDut(pmos_hvt(MosParams()), MosType.PMOS),
    ]

    # Dut = pmos_v5(IoMosParams()) # Default params 
    # Dut = pmos(MosParams()) # Default params 
    # NMOS = False  # FIXME: get this value, somewhere

    for dut in duts:
        res = iv(dut)
        print(res)

    # And munge some results 
    res = res.an[0]  # Get the DC sweep
    print(res.measurements)
    id = np.abs(res.data["xtop.vd:p"])
    gm = np.diff(id) / 10e-3
    gm_over_id = gm / id[:-1]

    # Save it to a plot
    fig, ax = plt.subplots()
    ax.plot(gm_over_id)
    fig.savefig("gm_over_id.png")
    # np.save("gm_over_id.npy", gm_over_id)


def iv(Dut: MosDut) -> hs.SimResult:
    """ Create and return an IV Curve Sim """ 

    @h.module
    class Tb:
        VSS = h.Port()  # The testbench interface: sole port VSS

        dut = Dut.dut(s=VSS, b=VSS)
        vd = Vdc(Vdc.Params(dc="polarity * vds"))(p=dut.d, n=VSS)
        vg = Vdc(Vdc.Params(dc="polarity * vgs", ac=1))(p=dut.g, n=VSS)

    sim = Sim(tb=Tb, attrs=s130.install.include(Corner.TYP))
    vgs = sim.param(name="vgs", val=1800 * m)
    vds = sim.param(name="vds", val=1800 * m)
    polarity = sim.param(name="polarity", val=1 if Dut.mostype == MosType.NMOS else -1) 
    dc = sim.dc(var=vgs, sweep=LinearSweep(start=0, stop=2500 * m, step=10 * m), name="dc")
    ac = sim.ac(sweep=LogSweep(start=1, stop=1*e(12), npts=100))
    # sim.meas(ac, "igate_at_1M", "find 'mag(i(xtop.vg))' at=1e6")
    # sim.meas(ac, "cin", "param='igate_at_1M / 2 / 3.14159 / 1e6'")

    return sim.run(sim_options)
