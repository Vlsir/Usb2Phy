from dataclasses import replace
from pprint import pprint

# Hdl Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.pdk import Corner
from hdl21.prefix import m, µ, f, T

# PDK Imports
import s130
import sitepdks as _

# Local Imports
from . import OpAmp5T
from ..tetris.mos import Nmos, Pmos
from ..pvt import Pvt
from ..tests.sim_test_mode import SimTest
from ..tests.sim_options import sim_options


@h.paramclass
class BalunParams:
    vc = h.Param(dtype=h.Prefixed, desc="Common-Mode Voltage", default=0 * m)


@h.generator
def Balun(p: BalunParams) -> h.Module:
    @h.module
    class Balun:
        diff = h.Diff(port=True, role=h.Diff.Roles.SOURCE)
        VSS = h.Port()
        vc = h.Vdc(dc=p.vc, ac=0)(n=VSS)
        vp = h.Vdc(dc=0, ac=500 * m)(p=diff.p, n=vc.p)
        vn = h.Vdc(dc=0, ac=-500 * m)(p=diff.n, n=vc.p)

    return Balun


@h.paramclass
class TbParams:
    # Required
    dut = h.Param(dtype=OpAmp5T.Params, desc="Amp Under Test")

    # Optional
    pvt = h.Param(dtype=Pvt, desc="Pvt Conditions", default=Pvt())
    ib = h.Param(dtype=h.Prefixed, desc="Bias Current Value (A)", default=1 * µ)
    vc = h.Param(dtype=h.Prefixed, desc="Common-Mode Input (V)", default=900 * m)
    cl = h.Param(dtype=h.Prefixed, desc="Load Cap (Single-Ended) (F)", default=50 * f)


@h.generator
def Tb(params: TbParams) -> h.Module:
    """Amp Testbench"""

    # Create our testbench
    tb = hs.tb("Tb")
    # Generate and drive VDD
    tb.VDD = VDD = h.Signal()
    tb.vvdd = h.Vdc(dc=1800 * m)(p=tb.VDD, n=tb.VSS)

    # Input voltage
    tb.inp = h.Diff()

    ## FIXME! we need different stimulus for Ac vs Tran, manage swapping between these
    ## For Ac: the "balun"
    tb.balun = Balun(vc=params.vc)(diff=tb.inp, VSS=tb.VSS)
    ## For Tran: generate a differential clock pattern
    # tb.ckg = DiffClkGen(
    #     period=4 * n, delay=0 * m, vd=200 * m, vc=200 * m, trf=800 * PICO
    # )(ck=tb.inp, VSS=tb.VSS)

    # Output & Load Caps
    tb.out = h.Signal()
    tb.cl = h.Cap(c=params.cl)(p=tb.out, n=tb.VSS)

    # Bias Current
    tb.ii1 = h.Idc(dc=params.ib)(p=tb.VSS)

    # Create the Pre-Amp DUT
    tb.dut = OpAmp5T(params.dut)(
        inp=tb.inp,
        out=tb.out,
        ibias=tb.ii1.n,
        VDD=tb.VDD,
        VSS=tb.VSS,
    )
    return tb


def sim(params: TbParams):
    """# OpAmp5T Sims"""

    # Create our parametric testbench
    tb_ = Tb(params)
    s130.compile(tb_)

    # And simulation input for it
    @hs.sim
    class OpAmp5TSim:
        tb = tb_
        op = hs.Op()
        # tr = hs.Tran(tstop=20 * n)
        ac = hs.Ac(sweep=hs.LogSweep(start=1, stop=1 * T, npts=10))
        dc_gain = hs.Meas(analysis=ac, expr="find 'vdb(xtop.out)' at=1")
        ugbw = hs.Meas(analysis=ac, expr="when vdb(xtop.out)=0")

    OpAmp5TSim.add(*s130.install.include(Corner.TYP))

    # Run some spice
    opts = replace(sim_options, rundir="./scratch")
    results = OpAmp5TSim.run(opts)
    ac_result = results.an[1]
    pprint(ac_result.data.keys())
    pprint(ac_result.measurements)

    import numpy as np
    import matplotlib.pyplot as plt

    plt.plot(ac_result.freq, np.abs(ac_result.data["xtop.out"]))
    plt.xscale("log")
    plt.yscale("log")
    plt.savefig("scratch/OpAmp5T.ac.png")


class Test(SimTest):
    """# Test Class"""

    tbgen = Tb

    def default_params(self) -> TbParams:
        return TbParams(
            dut=OpAmp5T.Params(
                mostype=h.MosType.NMOS,
                bias=Nmos(nser=8, npar=2),
                inp=Nmos(nser=8, npar=2),
                load=Pmos(nser=8, npar=2),
            ),
            # All other values are defaults
        )

    def typ(self):
        return sim(self.default_params())
