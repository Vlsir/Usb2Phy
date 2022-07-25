""" 
# ILO Tests 
"""

from typing import Optional

# Hdl & PDK Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.pdk import Corner
from hdl21.prefix import m, µ, f, n, T, PICO
from hdl21.primitives import Vdc, Vpulse, Idc
import s130
import sitepdks as _

from ...tests.supplyvals import SupplyVals
from ...tests.vcode import Vcode

# DUT Imports
from .ilo import Ilo, IloParams


@h.paramclass
class Pvt:
    """Process, Voltage, and Temperature Parameters"""

    p = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    v = h.Param(dtype=Corner, desc="Voltage Corner", default=Corner.TYP)
    t = h.Param(dtype=int, desc="Simulation Temperature (C)", default=25)


@h.paramclass
class TbParams:
    pvt = h.Param(dtype=Pvt, desc="PVT Conditions", default=Pvt())
    ilo = h.Param(dtype=IloParams, desc="Ilo Generator Parameters", default=IloParams())
    ib = h.Param(dtype=h.ScalarOption, desc="Bias Current", default=120 * µ)
    code = h.Param(dtype=int, desc="Fctrl Dac Code", default=16)


def IloSharedTb(params: TbParams, name: Optional[str] = None) -> h.Module:
    """
    # Shared Portions of Ilo Testbenches
    Note this is *not* an Hdl21 Generator, on purpose.
    """

    # Create our testbench
    tb = h.sim.tb(name or "IloTb")

    # Generate and drive VDD
    supplyvals = SupplyVals.corner(params.pvt.v)
    tb.VDDA33 = VDDA33 = h.Signal()
    tb.VDD18 = VDD18 = h.Signal()
    tb.vvdd18 = Vdc(dc=supplyvals.VDD18)(p=VDD18, n=tb.VSS)
    tb.vvdd33 = Vdc(dc=supplyvals.VDDA33)(p=VDDA33, n=tb.VSS)

    # Create the test-bench level delay stage signals
    tb.stg0 = stg0 = h.Diff()
    tb.stg1 = stg1 = h.Diff()
    tb.stg2 = stg2 = h.Diff()
    tb.stg3 = stg3 = h.Diff()

    # Bias Generation
    tb.pbias = pbias = h.Signal()
    # Pmos Side Bias
    tb.ii = Idc(Idc.Params(dc=1 * params.ib))(p=pbias, n=tb.VSS)

    # Frequency Control Dac Code
    tb.fctrl = fctrl = h.Signal(width=5)
    tb.vfctrl = Vcode(code=params.code, width=5, vhi=supplyvals.VDD18)(
        code=fctrl, VSS=tb.VSS
    )

    # Create the injection-pulse *Signal*, but not its driver
    tb.inj = h.Signal()

    # Create the Ilo DUT
    tb.dut = Ilo(params.ilo)(
        fctrl=fctrl,
        inj=tb.inj,
        pbias=pbias,
        stg0=stg0,
        stg1=stg1,
        stg2=stg2,
        stg3=stg3,
        VDDA33=VDDA33,
        VDD18=VDD18,
        VSS=tb.VSS,
    )
    return tb



@h.generator
def IloFreqTb(params: TbParams) -> h.Module:
    """Ilo Frequency Testbench"""

    # Create our testbench
    tb = IloSharedTb(params=params, name="IloFreqTb")

    # Create the injection-pulse source, which in this bench serves entirely as a kick-start
    tb.vinj = Vpulse(
        Vpulse.Params(
            v1=1800 * m,
            v2=0,
            period=1001,  # "Infinite" period
            rise=10 * PICO,
            fall=10 * PICO,
            width=1000,
            delay=10 * PICO,
        )
    )(p=tb.inj, n=tb.VSS)

    return tb


def sim_input(tbgen: h.Generator, params: TbParams) -> hs.Sim:
    """Ilo Frequency Sim"""

    # Create some simulation stimulus
    @hs.sim
    class IloSim:
        # The testbench
        tb = tbgen(params)

        # Our sole analysis: transient, for much longer than we need.
        # But auto-stopping when measurements complete.
        tr = hs.Tran(tstop=500 * n)

        # Measurements
        trise5 = hs.Meas(tr, expr="when 'V(xtop.stg0_p)-V(xtop.stg0_n)'=0 rise=5")
        trise15 = hs.Meas(tr, expr="when 'V(xtop.stg0_p)-V(xtop.stg0_n)'=0 rise=15")
        tperiod = hs.Meas(tr, expr="param='(trise15-trise5)/10'")
        idd = hs.Meas(tr, expr="avg I(xtop.vvdd) from=trise5 to=trise15")

        # The stuff we can't first-class represent, and need to stick in a literal.
        l = hs.Literal(
            f"""
            simulator lang=spice
            .temp {params.pvt.t}
            .option autostop
            simulator lang=spectre
        """
        )
        i = hs.Include(
            "/tools/B/dan_fritchman/dev/VlsirWorkspace/Usb2Phy/Usb2PhyAna/resources/scs130lp.sp"
        )

    # Add the PDK dependencies
    IloSim.add(*s130.install.include(params.pvt.p))

    return IloSim


def idd(results: hs.SimResult) -> float:
    return results.an[0].measurements["idd"]


def tperiod(results: hs.SimResult) -> float:
    return results.an[0].measurements["tperiod"]
