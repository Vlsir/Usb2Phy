from dataclasses import replace
from pprint import pprint

# Hdl Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.prefix import m, µ

# PDK Imports
import s130
import sitepdks as _

# Local Imports
from . import PmosBiasDist
from ..tetris.mos import Pmos
from ..pvt import Pvt
from ..tests.sim_test_mode import SimTest, SimTestMode
from ..tests.sim_options import sim_options


@h.paramclass
class TbParams:
    dut = h.Param(dtype=PmosBiasDist.Params, desc="DUT Parameters")
    pvt = h.Param(dtype=Pvt, desc="Pvt Conditions", default=Pvt())
    ib = h.Param(dtype=h.Prefixed, desc="Bias Current Value (A)", default=1 * µ)


@h.generator
def Tb(params: TbParams) -> h.Module:
    """Bias Distribution Testbench"""

    # Create our testbench
    tb = hs.tb("Tb")
    # Generate and drive VDD
    tb.VDD = VDD = h.Signal()
    tb.vvdd = h.Vdc(dc=1800 * m)(p=tb.VDD, n=tb.VSS)

    # Output
    num_output_taps = len(params.dut.taps)
    tb.out = h.Signal(width=num_output_taps)
    tb.vouts = num_output_taps * h.Vdc(dc=900 * m)(p=tb.out, n=tb.VSS)

    # Bias Current
    tb.ii1 = h.Idc(dc=params.ib)(n=tb.VSS)
    tb.ii2 = h.Idc(dc=params.ib)(n=tb.VSS)

    # Create the DUT
    tb.dut = PmosBiasDist(params.dut)(
        iout=tb.out,
        iin_casc=tb.ii1.p,
        iin_top=tb.ii2.p,
        VDD=tb.VDD,
        VSS=tb.VSS,
    )
    return tb


def sim(params: TbParams):
    """# PmosBiasDist Sims"""

    # Create our parametric testbench
    tb_ = Tb(params)
    s130.compile(tb_)

    # And simulation input for it
    @hs.sim
    class Sim:
        tb = tb_
        op = hs.Op()

    # Run some spice
    Sim.add(*s130.install.include(params.pvt.p))
    opts = replace(sim_options, rundir="./scratch")
    results = Sim.run(opts)
    pprint(results)


class Test(SimTest):
    """# PmosBiasDist Test Class"""

    tbgen = Tb

    def default_params(self) -> TbParams:
        return TbParams(
            dut=PmosBiasDist.Params(
                # iin=1*µ,
                pbias=Pmos(nser=8, npar=1),
                pcasc=Pmos(nser=4, npar=1),
                pcdiode=Pmos(nser=16),
                taps=[1, 1, 1, 1],
            )
        )

    def typ(self):
        return sim(self.default_params())
