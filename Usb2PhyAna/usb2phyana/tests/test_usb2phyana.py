""" 
# USB 2.0 Phy Custom / Analog Tests 
"""

# Std-Lib Imports
import io

# Hdl Imports
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.prefix import NANO

# Local Imports
from .. import Usb2PhyAna, AnaDigBundle
from ..phyroles import PhyRoles
from ..supplies import PhySupplies
from ..other import PhyBias
from .sim_test_mode import SimTest
from ..tests.sim_options import sim_options


@h.paramclass
class Pvt:
    """Process, Voltage, and Temperature Parameters"""

    p = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    v = h.Param(dtype=Corner, desc="Voltage Corner", default=Corner.TYP)
    t = h.Param(dtype=int, desc="Simulation Temperature (C)", default=25)


@h.paramclass
class TbParams:
    pvt = h.Param(dtype=Pvt, desc="PVT Conditions", default=Pvt())


@h.generator
def PhyTb(params: TbParams) -> h.Module:
    # Create our testbench
    tb = h.sim.tb(name="HsRxTb")

    tb.SUPPLIES = PhySupplies(role=PhyRoles.PHY, desc="Supplies")
    tb.pads = h.Diff(role=None, desc="Differential Pads")
    tb.dig_if = AnaDigBundle(desc="Analog-Digital Interface")
    tb.refck = h.Diff(role=h.Diff.Roles.SINK, desc="Reference Clock")
    tb.bypck = h.Diff(role=h.Diff.Roles.SINK, desc="TX PLL Bypass Clock")
    tb.bias = PhyBias(role=PhyRoles.PHY, desc="Phy Bias Input(s)")

    tb.phy = Usb2PhyAna(h.Default)(
        SUPPLIES=tb.SUPPLIES,
        pads=tb.pads,
        dig_if=tb.dig_if,
        refck=tb.refck,
        bypck=tb.bypck,
        bias=tb.bias,
    )

    return tb


def sim_phy():
    import s130
    import sitepdks as _

    params = TbParams()
    phy_tb = PhyTb(params)
    h.pdk.compile(phy_tb)

    # Create some simulation stimulus
    @h.sim.sim
    class PhySim:
        # The testbench
        tb = phy_tb

        # Our sole analysis: transient
        tr = h.sim.Tran(tstop=50 * NANO)

        # The stuff we can't first-class represent, and need to stick in a literal.
        l = h.sim.Literal(
            f"""
            simulator lang=spice
            .temp {params.pvt.t}
            simulator lang=spectre
        """
        )
        i = h.sim.Include(s130.resources / "stdcells.sp")

    # Add the PDK dependencies
    PhySim.add(*s130.install.include(params.pvt.p))

    results = PhySim.run(sim_options)
    print(results)


class TestPhy(SimTest):
    """PHY Top-Level Tests"""

    tbgen = PhyTb

    def min(self):
        return self.netlist()

    def typ(self):
        return sim_phy()

    def max(self):
        # FIXME: add corner runs
        raise NotImplementedError
