import io, copy
from pathlib import Path
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
from hdl21.prefix import e, m, µ, UNIT
from hdl21.primitives import MosType, Vdc

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
        v = Vdc(Vdc.Params(dc=1800 * m, ac=0 * m))(p=VDD, n=VSS)

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


@dataclass
class MosDut:
    """Dut info for the IV Curve Test"""

    dut: h.Instantiable
    mostype: MosType


def test_iv():
    """I-V Curve Test"""

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


def iv(Dut: MosDut) -> hs.SimResult:
    """Create and return an IV Curve Sim"""

    @h.module
    class Tb:
        VSS = h.Port()  # The testbench interface: sole port VSS

        dut = Dut.dut(s=VSS, b=VSS)
        vd = Vdc(Vdc.Params(dc="polarity * vds", ac=0 * m))(p=dut.d, n=VSS)
        vg = Vdc(Vdc.Params(dc="polarity * vgs", ac=1 * UNIT))(p=dut.g, n=VSS)

    sim = Sim(tb=Tb, attrs=s130.install.include(Corner.TYP))
    vgs = sim.param(name="vgs", val=1800 * m)
    vds = sim.param(name="vds", val=1800 * m)
    polarity = sim.param(name="polarity", val=1 if Dut.mostype == MosType.NMOS else -1)
    dc = sim.dc(
        var=vgs, sweep=LinearSweep(start=0, stop=2500 * m, step=10 * m), name="dc"
    )
    # ac = sim.ac(sweep=LogSweep(start=1, stop=1 * e(12), npts=100))
    # sim.meas(ac, "igate_at_1M", "find 'mag(i(xtop.vg))' at=1e6")
    # sim.meas(ac, "cin", "param='igate_at_1M / 2 / 3.14159 / 1e6'")

    return sim.run(sim_options)


def postprocess(dut: MosDut, result: hs.SimResult) -> None:
    """Post-process and plot results from an `iv()` run on `dut`."""
    result = result.an[0]  # Get the DC sweep
    print(result.measurements)

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
    fig.savefig(f"scratch/gm_over_id.{dut.dut.name}.png")
    # np.save("scratch/gm_over_id.npy", gm_over_id)
