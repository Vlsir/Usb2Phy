""" 
# Slicer Tests 
"""

# Hdl & PDK Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21 import Diff
from hdl21.pdk import Corner
from hdl21.sim import Sim, LogSweep
from hdl21.prefix import m, µ, f, n, PICO
from hdl21.primitives import Vdc, Idc, C, Vpulse
import s130
import sitepdks as _

from ...tests.sim_options import sim_options
from ...tests.diffclockgen import DiffClkGen, DiffClkParams

# DUT Imports
from .slicer import Slicer


@h.paramclass
class Pvt:
    """Process, Voltage, and Temperature Parameters"""

    p = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    v = h.Param(dtype=h.Prefixed, desc="Supply Voltage Value (V)", default=1800 * m)
    t = h.Param(dtype=int, desc="Simulation Temperature (C)", default=25)


@h.paramclass
class TbParams:
    pvt = h.Param(
        dtype=Pvt, desc="Process, Voltage, and Temperature Parameters", default=Pvt()
    )
    vd = h.Param(dtype=h.Prefixed, desc="Differential Voltage (V)", default=100 * m)
    vc = h.Param(dtype=h.Prefixed, desc="Common-Mode Voltage (V)", default=900 * m)
    cl = h.Param(dtype=h.Prefixed, desc="Load Cap (Single-Ended) (F)", default=5 * f)


@h.generator
def SlicerTb(p: TbParams) -> h.Module:
    """Slicer Testbench"""

    # Create our testbench
    tb = h.sim.tb("SlicerTb")
    # Generate and drive VDD
    tb.VDD = VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=p.pvt.v, ac=0 * m))(p=VDD, n=tb.VSS)

    # Input-driving balun
    tb.inp = Diff()
    tb.inpgen = DiffClkGen(
        DiffClkParams(period=4 * n, delay=1 * n, vc=p.vc, vd=p.vd, trf=800 * PICO)
    )(ck=tb.inp, VSS=tb.VSS)

    # Clock generator
    tb.clk = clk = h.Signal()
    tb.vclk = Vpulse(
        Vpulse.Params(
            delay=0,
            v1=0,
            v2=p.pvt.v,
            period=2 * n,
            rise=1 * PICO,
            fall=1 * PICO,
            width=1 * n,
        )
    )(p=clk, n=tb.VSS)

    # Output & Load Caps
    tb.out = Diff()
    Cload = C(C.Params(c=p.cl))
    tb.clp = Cload(p=tb.out.p, n=tb.VSS)
    tb.cln = Cload(p=tb.out.n, n=tb.VSS)

    # Create the Slicer DUT
    tb.dut = Slicer(
        inp=tb.inp,
        out=tb.out,
        clk=clk,
        VDD18=VDD,
        VSS=tb.VSS,
    )
    return tb


def test_slicer_sim():
    """Slicer Test(s)"""

    # Create our parametric testbench
    params = TbParams(pvt=Pvt(), vc=900 * m, vd=1 * m)

    # Create our simulation input
    @hs.sim
    class SlicerSim:
        tb = SlicerTb(params)
        tr = hs.Tran(tstop=12 * n)

    # Add the PDK dependencies
    SlicerSim.add(*s130.install.include(params.pvt.p))

    # Run some spice
    results = SlicerSim.run(sim_options)
    print(results)
