
""" 
# Slicer Tests 
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.sim import Sim, LogSweep
from hdl21.prefix import m, µ, f, n, T
from hdl21.primitives import Vdc, Idc, C
import s130 
import sitepdks as _

from ...tests.sim_options import sim_options

# DUT Imports
from .slicer import Slicer
from .. import Diff


@h.paramclass
class Pvt:
    """ Process, Voltage, and Temperature Parameters """

    p = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    v = h.Param(dtype=h.Prefixed, desc="Supply Voltage Value (V)", default=1800*m)
    t = h.Param(dtype=int, desc="Simulation Temperature (C)", default=25)


@h.paramclass
class TbParams:
    pvt = h.Param(dtype=Pvt, desc="Process, Voltage, and Temperature Parameters", default=Pvt())
    vc = h.Param(dtype=h.Prefixed, desc="Common-Mode Voltage (V)", default=200 * m)
    cl = h.Param(dtype=h.Prefixed, desc="Load Cap (Single-Ended) (F)", default=50 * f)


@h.generator
def SlicerTb(p: TbParams) -> h.Module:
    """ Slicer Testbench """

    # Create our testbench 
    tb = h.sim.tb("SlicerTb")
    # Generate and drive VDD
    tb.VDD = VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=p.pvt.v))(p=VDD, n=tb.VSS)

    # Input-driving balun
    tb.inp = Diff()
    tb.vinp = Vdc(Vdc.Params(dc=p.vc, ac=1))(p=tb.inp.p, n=tb.VSS)
    tb.vinn = Vdc(Vdc.Params(dc=p.vc, ac=-1))(p=tb.inp.n, n=tb.VSS)

    # Clock generator
    tb.clk = clk = h.Signal()
    tb.vclk = Vdc(Vdc.Params(dc=p.pvt.v))(p=clk, n=tb.VSS)
    
    # Output & Load Caps
    tb.out = Diff()
    Cload = C(C.Params(c=p.cl))
    tb.clp = Cload(p=tb.out.p, n=tb.VSS)
    tb.cln = Cload(p=tb.out.n, n=tb.VSS)

    # Create the Slicer DUT 
    tb.dut = Slicer(
         inp=tb.inp, out=tb.out, clk=clk, VDD18=VDD, VSS=tb.VSS,
    )
    return tb


def test_slicer_sim():
    """ Slicer Test(s) """

    # Create our parametric testbench 
    params = TbParams(pvt=Pvt(), vc=900*m)
    tb = SlicerTb(params)

    # And simulation input for it 
    sim = Sim(tb=tb, attrs=s130.install.include(Corner.TYP))
    # sim.op()
    ac = sim.ac(sweep=LogSweep(start=1, stop=1*T, npts=100))
    # sim.meas(ac, "dc_gain", "find 'vdb(xtop.out_p, xtop.out_n)' at=1")
    
    # Run some spice
    results = sim.run(sim_options)
    print(results)
