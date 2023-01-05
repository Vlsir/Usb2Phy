from dataclasses import replace
from pprint import pprint

# Hdl Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.pdk import Corner
from hdl21.prefix import m, µ, f, n, T, PICO

# PDK Imports
import s130
import sitepdks as _

# Local Imports
from .fcasc import Fcasc, UnityGainBuffer
from ..pvt import Pvt
from ..tests.sim_test_mode import SimTest, SimTestMode
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
    pvt = h.Param(dtype=Pvt, desc="Pvt Conditions", default=Pvt())
    ib = h.Param(dtype=h.Prefixed, desc="Bias Current Value (A)", default=1 * µ)
    vc = h.Param(dtype=h.Prefixed, desc="Common-Mode Voltage (V)", default=900 * m)
    cl = h.Param(dtype=h.Prefixed, desc="Load Cap (Single-Ended) (F)", default=50 * f)


@h.generator
def FcascTb(params: TbParams) -> h.Module:
    """Amp Testbench"""

    # Create our testbench
    tb = hs.tb("FcascTb")
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
    tb.ii2 = h.Idc(dc=params.ib)(p=tb.VSS)

    # Create the Pre-Amp DUT
    tb.dut = Fcasc(h.Default)(
        inp=tb.inp,
        out=tb.out,
        ibias1=tb.ii1.n,
        ibias2=tb.ii2.n,
        VDD=tb.VDD,
        VSS=tb.VSS,
    )
    return tb


def sim_fcasc():
    """# Fcasc Sims"""

    # Create our parametric testbench
    tb_ = FcascTb(TbParams())
    s130.compile(tb_)

    # And simulation input for it
    @hs.sim
    class FcascSim:
        tb = tb_
        op = hs.Op()
        # tr = hs.Tran(tstop=20 * n)
        ac = hs.Ac(sweep=hs.LogSweep(start=1, stop=1 * T, npts=10))
        dc_gain = hs.Meas(analysis=ac, expr="find 'vdb(xtop.out)' at=1")
        ugbw = hs.Meas(analysis=ac, expr="when vdb(xtop.out)=0")

    FcascSim.add(*s130.install.include(Corner.TYP))

    # Run some spice
    opts = replace(sim_options, rundir="./scratch")
    results = FcascSim.run(opts)
    ac_result = results.an[1]
    pprint(ac_result.data.keys())
    pprint(ac_result.measurements)

    import numpy as np
    import matplotlib.pyplot as plt

    plt.plot(ac_result.freq, np.abs(ac_result.data["xtop.out"]))
    plt.xscale("log")
    plt.yscale("log")
    plt.savefig("scratch/Fcasc.ac.png")


# def test_fcasc():
#     return sim_fcasc()


@h.generator
def UnityGainTb(params: TbParams) -> h.Module:
    """Unity-Gain Amp Testbench"""

    # Create our testbench
    tb = hs.tb("UnityGainTb")
    # Generate and drive VDD
    tb.VDD = VDD = h.Signal()
    tb.vvdd = h.Vdc(dc=1800 * m)(p=tb.VDD, n=tb.VSS)

    # Input voltage
    tb.inp = h.Signal()
    tb.vinp = h.Vdc(dc=params.vc, ac=1)(p=tb.inp, n=tb.VSS)

    # Output & Load Caps
    tb.out = h.Signal()
    tb.cl = h.Cap(c=params.cl)(p=tb.out, n=tb.VSS)

    # Bias Current
    tb.ii1 = h.Idc(dc=params.ib)(p=tb.VSS)
    tb.ii2 = h.Idc(dc=params.ib)(p=tb.VSS)

    # Create the Pre-Amp DUT
    tb.dut = UnityGainBuffer(h.Default)(
        inp=tb.inp,
        out=tb.out,
        ibias1=tb.ii1.n,
        ibias2=tb.ii2.n,
        VDD=tb.VDD,
        VSS=tb.VSS,
    )
    return tb


def sim_unity_gain_buffer():
    """# UnityGain Sims"""

    # Create our parametric testbench
    tb_ = UnityGainTb(TbParams())
    s130.compile(tb_)

    # And simulation input for it
    @hs.sim
    class UnityGainSim:
        tb = tb_
        op = hs.Op()
        # tr = hs.Tran(tstop=20 * n)
        ac = hs.Ac(sweep=hs.LogSweep(start=1, stop=1 * T, npts=10))
        dc_gain = hs.Meas(analysis=ac, expr="find 'vdb(xtop.out)' at=1")

    UnityGainSim.add(*s130.install.include(Corner.TYP))

    # Run some spice
    opts = replace(sim_options, rundir="./scratch")
    results = UnityGainSim.run(opts)
    op_result = results.an[0]
    print(op_result)
    ac_result = results.an[1]
    pprint(ac_result.measurements)

    import numpy as np
    import matplotlib.pyplot as plt

    plt.plot(ac_result.freq, np.abs(ac_result.data["xtop.out"]))
    plt.xscale("log")
    plt.yscale("log")
    plt.savefig("scratch/UnityGain.ac.png")


def test_unity_gain_buffer():
    return sim_unity_gain_buffer()


# class UnityGainTest(SimTest):
#     tbgen = UnityGainTb

#     def typ(self):
#         return sim_unity_gain_buffer()
