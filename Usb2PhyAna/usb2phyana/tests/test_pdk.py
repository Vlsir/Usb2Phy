import io
from dataclasses import dataclass, replace

# PyPi Imports
import numpy as np
import matplotlib.pyplot as plt

# HDL Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.pdk import Corner
from hdl21.sim import Sim, LinearSweep
from hdl21.prefix import m, µ, UNIT
from hdl21.primitives import MosType, Vdc, Nmos, Pmos

# PDK Imports
import sitepdks as _
import s130
from s130 import MosParams, IoMosParams

# Local Imports
from .sim_options import sim_options
from ..tests.sim_test_mode import SimTestMode

nmos = s130.modules.nmos
nmos_lvt = s130.modules.nmos_lvt
pmos = s130.modules.pmos
pmos_hvt = s130.modules.pmos_hvt
pmos_v5 = s130.modules.pmos_v5


def test_pdk(simtestmode: SimTestMode):
    """Non-PHY test that we can execute simulations with the installed PDK"""

    @h.module
    class Tb:
        VSS = h.Port()  # The testbench interface: sole port VSS

        VDD = h.Signal()
        v = Vdc(dc=1800 * m)(p=VDD, n=VSS)

        inmos = nmos(MosParams())(d=VDD, g=VDD, s=VSS, b=VSS)
        inmos_lvt = nmos_lvt(MosParams())(d=VDD, g=VDD, s=VSS, b=VSS)
        ipmos = pmos(MosParams())(d=VSS, g=VSS, s=VDD, b=VDD)
        ipmos_hvt = pmos_hvt(MosParams())(d=VSS, g=VSS, s=VDD, b=VDD)
        ipmos_v5 = pmos_v5(IoMosParams())(d=VSS, g=VSS, s=VDD, b=VDD)

    if simtestmode == SimTestMode.NETLIST:
        h.netlist(Tb, dest=io.StringIO())
    else:
        sim = Sim(tb=Tb, attrs=s130.install.include(Corner.TYP))
        sim.tran(tstop=1 * µ, name="tran1")
        sim.run(sim_options)


def test_pdk_compile(simtestmode: SimTestMode):
    """Non-PHY test that we can execute simulations with the installed PDK"""

    @h.module
    class Tb:
        VSS = h.Port()  # The testbench interface: sole port VSS

        VDD = h.Signal()
        v = Vdc(dc=1800 * m)(p=VDD, n=VSS)

        # Instantiate hdl21.primitives Generic Devices
        inmos = Nmos()(d=VDD, g=VDD, s=VSS, b=VSS)
        inmos_lvt = Nmos(vth=h.MosVth.LOW)(d=VDD, g=VDD, s=VSS, b=VSS)
        ipmos = Pmos()(d=VSS, g=VSS, s=VDD, b=VDD)
        ipmos_hvt = Pmos(vth=h.MosVth.HIGH)(d=VSS, g=VSS, s=VDD, b=VDD)
        ipmos_v5 = Pmos(model="v5")(d=VSS, g=VSS, s=VDD, b=VDD)

    # Compile it into the target in-memory PDK
    h.pdk.compile(Tb)

    if simtestmode == SimTestMode.NETLIST:
        h.netlist(Tb, dest=io.StringIO())
    else:
        sim = Sim(tb=Tb, attrs=s130.install.include(Corner.TYP))
        sim.tran(tstop=1 * µ, name="tran1")
        sim.run(sim_options)


@dataclass
class MosDut:
    """# Mos "Design" Under Test"""

    mos: h.Instantiable
    mostype: MosType


def test_iv(simtestmode: SimTestMode):
    """I-V Curve Test"""
    if simtestmode == SimTestMode.NETLIST:
        return  # Nothing to do here

    duts = [
        MosDut(nmos(MosParams()), MosType.NMOS),
        MosDut(nmos_lvt(MosParams()), MosType.NMOS),
        MosDut(pmos(MosParams()), MosType.PMOS),
        MosDut(pmos_hvt(MosParams()), MosType.PMOS),
        MosDut(pmos_v5(IoMosParams()), MosType.PMOS),
    ]

    for dut in duts:
        # Run some I-V simulation
        result = iv(dut)
        # And munge some results
        postprocess(dut, result)


def iv(mosdut: MosDut) -> hs.SimResult:
    """Create and return an IV Curve Sim"""

    @h.module
    class MosIvTb:
        VSS = h.Port()  # The testbench interface: sole port VSS

        mos = mosdut.mos(s=VSS, b=VSS)  # The transistor under test
        vd = Vdc(dc="polarity * vds")(p=mos.d, n=VSS)
        vg = Vdc(dc="polarity * vgs", ac=1)(p=mos.g, n=VSS)

    @hs.sim
    class MosIvSim:
        tb = MosIvTb
        vgs = hs.Param(val=1800 * m)
        vds = hs.Param(val=1800 * m)
        polarity = hs.Param(val=1 if mosdut.mostype == MosType.NMOS else -1)
        dc = hs.Dc(var=vgs, sweep=LinearSweep(start=0, stop=2500 * m, step=10 * m))

    MosIvSim.add(*s130.install.include(Corner.TYP))
    return MosIvSim.run(sim_options)


def postprocess(dut: MosDut, result: hs.SimResult) -> None:
    """Post-process and plot results from an `iv()` run on `dut`."""
    result = result.an[0]  # Get the DC sweep
    step = float(10 * m)  # FIXME: get this from the sweep above

    id = np.abs(result.data["xtop.vd:p"])
    gm = np.diff(id) / step
    gm_over_id = gm / id[:-1]
    vgs = [1e3 * step * idx for idx in range(len(gm_over_id))]

    # Save it to a plot
    fig, ax = plt.subplots()
    ax2 = ax.twinx()
    ax.plot(vgs, gm_over_id)
    ax.set_xlabel("Vgs (mV)")
    ax.set_ylabel("gm / Id")
    ax2.plot(vgs, 1e6 * id[:-1])
    ax2.set_ylabel("Id (µA)")
    ax2.set_yscale("log")
    ax.grid()
    fig.savefig(f"scratch/gm_over_id.{dut.mos.name}.png")
    # np.save("scratch/gm_over_id.npy", gm_over_id)
