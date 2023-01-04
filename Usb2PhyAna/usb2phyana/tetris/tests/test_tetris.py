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
import s130
import sitepdks as _

# Local Imports
from ...tests.sim_options import sim_options
from ...tests.sim_test_mode import SimTestMode
from ..mos import Nmos, Pmos


def test_tetris1():

    h.elaborate(
        [
            Nmos(nser=1),
            Nmos(nser=2),
            Nmos(nser=4),
            Nmos(nser=8),
            Nmos(nser=16),
        ]
    )

    h.elaborate(
        [
            Pmos(nser=1),
            Pmos(nser=2),
            Pmos(nser=4),
            Pmos(nser=8),
            Pmos(nser=16),
        ]
    )


@dataclass
class MosDut:
    """# Mos "Design" Under Test"""

    mos: h.Instantiable
    tp: MosType


def test_iv(simtestmode: SimTestMode):
    """I-V Curve Test"""
    if simtestmode == SimTestMode.NETLIST:
        return  # Nothing to do here
    run_iv_curves()


def run_iv_curves():
    duts = [
        MosDut(Pmos(nser=1, npar=1), h.MosType.PMOS),
        MosDut(Pmos(nser=2, npar=1), h.MosType.PMOS),
        MosDut(Pmos(nser=4, npar=1), h.MosType.PMOS),
        MosDut(Pmos(nser=8, npar=1), h.MosType.PMOS),
        MosDut(Pmos(nser=16, npar=1), h.MosType.PMOS),
    ]

    for dut in duts:
        # Run some I-V simulation
        result = iv(dut)
        # And munge some results
        postprocess(dut, result)


def iv(dut: MosDut) -> hs.SimResult:
    """Create and return an IV Curve Sim"""
    h.pdk.compile(dut.mos)

    @h.module
    class MosIvTb:
        VSS = h.Port()  # The testbench interface: sole port VSS

        mos = dut.mos(s=VSS, VSS=VSS, VDD=VSS)  # The transistor under test
        vd = Vdc(dc="polarity * vds")(p=mos.d, n=VSS)
        vg = Vdc(dc="polarity * vgs", ac=1)(p=mos.g, n=VSS)

    @hs.sim
    class MosIvSim:
        tb = MosIvTb
        vgs = hs.Param(val=1800 * m)
        vds = hs.Param(val=1800 * m)
        polarity = hs.Param(val=1 if dut.tp == MosType.NMOS else -1)
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
