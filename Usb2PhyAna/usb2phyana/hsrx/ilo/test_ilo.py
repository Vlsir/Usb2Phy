
""" 
# ILO Tests 
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.sim import Sim, LogSweep
from hdl21.prefix import m, µ, f, n, T, PICO
from hdl21.primitives import Vdc, Vpulse, Idc, C
import s130 
import sitepdks as _

from ...tests.sim_options import sim_options

# DUT Imports
from .ilo import Ilo
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
    cl = h.Param(dtype=h.Prefixed, desc="Load Cap (Per Stage) (F)", default=10 * f)


@h.generator
def IloTb(p: TbParams) -> h.Module:
    """ Ilo Testbench """

    # Create our testbench 
    tb = h.sim.tb("IloTb")

    # Generate and drive VDD
    tb.VDD = VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=p.pvt.v))(p=VDD, n=tb.VSS)

    # Create the injection-pulse source, 
    # which also serves as our kick-start
    tb.inj = h.Signal()
    tb.vinj = Vpulse(Vpulse.Params(
            v1=0,
            v2=1800*m,
            period=9900 * PICO,
            rise=10 * PICO,
            fall=10 * PICO,
            width=1500 * PICO,
            delay=0)
        )(p=tb.inj, n=tb.VSS)

    # Create the Ilo DUT 
    tb.dut = Ilo(
         inj=tb.inj, VDD18=VDD, VSS=tb.VSS,
    )
    return tb


def test_ilo_sim():
    """ Ilo Test(s) """

    # Create our parametric testbench 
    params = TbParams(pvt=Pvt(v=900*m), cl = 10*f)
    tb = IloTb(params)

    # And simulation input for it 
    sim = Sim(tb=tb, attrs=s130.install.include(Corner.TYP))
    sim.tran(tstop=20*n)
    
    # Run some spice
    results = sim.run(sim_options)
    print(results)
