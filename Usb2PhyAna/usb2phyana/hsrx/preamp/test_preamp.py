""" 
# RX Pre-Amp Tests 
"""

# Hdl & PDK Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.pdk import Corner
from hdl21.prefix import m, µ, f, n, T, PICO
from hdl21.primitives import Vdc, Idc, C
import s130
import sitepdks as _

from ...tests.sim_options import sim_options

# DUT Imports
from .preamp import PreAmp
from .. import Diff
from ...tests.diffclockgen import DiffClkGen, DiffClkParams


@h.paramclass
class BalunParams:
    vc = h.Param(dtype=h.Prefixed, desc="Common-Mode Voltage", default=0 * m)


@h.generator
def Balun(p: BalunParams) -> h.Module:
    @h.module
    class Balun:
        diff = Diff(port=True, role=Diff.Roles.SOURCE)
        VSS = h.Port()
        vc = Vdc(Vdc.Params(dc=p.vc, ac=0))(n=VSS)
        vp = Vdc(Vdc.Params(dc=0, ac=500 * m))(p=diff.p, n=vc.p)
        vn = Vdc(Vdc.Params(dc=0, ac=-500 * m))(p=diff.n, n=vc.p)

    return Balun


@h.paramclass
class Pvt:
    """Process, Voltage, and Temperature Parameters"""

    p = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    v = h.Param(dtype=h.Prefixed, desc="Supply Voltage Value (V)", default=3300 * m)
    t = h.Param(dtype=int, desc="Simulation Temperature (C)", default=25)


@h.paramclass
class TbParams:
    pvt = h.Param(
        dtype=Pvt, desc="Process, Voltage, and Temperature Parameters", default=Pvt()
    )
    ib = h.Param(dtype=h.Prefixed, desc="Bias Current Value (A)", default=1 * m)
    vc = h.Param(dtype=h.Prefixed, desc="Common-Mode Voltage (V)", default=200 * m)
    cl = h.Param(dtype=h.Prefixed, desc="Load Cap (Single-Ended) (F)", default=50 * f)


@h.generator
def PreAmpTb(p: TbParams) -> h.Module:
    """Pre-Amp Testbench"""

    # Create our testbench
    tb = h.sim.tb("PreAmpTb")
    # Generate and drive VDD
    tb.VDD = VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=p.pvt.v))(p=tb.VDD, n=tb.VSS)

    # Input voltage
    tb.inp = Diff()

    ## FIXME! we need different stimulus for Ac vs Tran, sort out how to manage
    ## For Ac: the "balnun"
    ## tb.balun = Balun(vc=p.vc)(diff=tb.inp, VSS=tb.VSS)
    ## For Tran: generate a differential clock pattern
    tb.ckg = DiffClkGen(period=4 * n, delay=0, vd=200 * m, vc=200 * m, trf=800 * PICO)(
        ck=tb.inp, VSS=tb.VSS
    )

    # Output & Load Caps
    tb.out = Diff()
    Cload = C(C.Params(c=p.cl))
    tb.clp = Cload(p=tb.out.p, n=tb.VSS)
    tb.cln = Cload(p=tb.out.n, n=tb.VSS)

    # Bias Current
    tb.ibias = ibias = h.Signal()
    tb.ii = Idc(Idc.Params(dc=p.ib))(
        p=ibias, n=tb.VSS
    )  # *Sinks* a current equal to `p.ib`.

    # Create the Pre-Amp DUT
    tb.dut = PreAmp(
        inp=tb.inp,
        out=tb.out,
        ibias=ibias,
        VDD33=tb.VDD,
        VSS=tb.VSS,
    )
    return tb


def test_preamp_sim():
    """Pre-Amp Test(s)"""

    # Create our parametric testbench
    params = TbParams(pvt=Pvt(), vc=200 * m, cl=10 * f, ib=200 * µ)

    # And simulation input for it
    @hs.sim
    class PreAmpSim:
        tb = PreAmpTb(params)
        op = hs.Op()
        ac = hs.Ac(sweep=hs.LogSweep(start=1, stop=1 * T, npts=100))
        tr = hs.Tran(tstop=20 * n)
        # dc_gain = hs.Meas(analysis=ac, expr="find 'vdb(xtop.out_p, xtop.out_n)' at=1")

    PreAmpSim.add(*s130.install.include(Corner.TYP))

    # Run some spice
    results = PreAmpSim.run(sim_options)

    # sim = Sim(tb=tb, attrs=s130.install.include(Corner.TYP))
    # sim.op()
    # ac = sim.ac(sweep=LogSweep(start=1, stop=1*T, npts=100))
    # # sim.meas(ac, "dc_gain", "find 'vdb(xtop.out_p, xtop.out_n)' at=1")
    # # Run some spice
    # results = sim.run(sim_options)

    print(results)
