"""
# CML Pulse Generator
## Unit Tests
"""

# Hdl & PDK Imports
import sitepdks as _
import s130
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.sim import Sim
from hdl21.prefix import m, p, n, K, f, µ
from hdl21.primitives import Vdc, Idc

# DUT Imports
from .pulsegen import CmlPulseGen, CmlParams
from ...cmlbuf import CmlBuf
from ...diff import Diff
from ...tests.diffclockgen import DiffClkGen, DiffClkParams
from ...tests.sim_options import sim_options


@h.paramclass
class Pvt:
    """Process, Voltage, and Temperature Parameters"""

    p = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    v = h.Param(dtype=h.Prefixed, desc="Supply Voltage Value (V)", default=1800 * m)
    t = h.Param(dtype=int, desc="Simulation Temperature (C)", default=25)


@h.paramclass
class TbParams:
    pvt = h.Param(dtype=Pvt, desc="Process, Voltage, and Temperature Parameters")
    cml = h.Param(dtype=CmlParams, desc="CML Parameters")


@h.generator
def CmlPulseGenTb(params: TbParams) -> h.Module:
    """CML Pulse Generator Testbench"""

    tb = h.sim.tb("CmlPulseGenTb")

    # Create and drive the supply
    tb.VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=params.pvt.v, ac=0 * m))(p=tb.VDD, n=tb.VSS)

    # Input clock generation
    tb.ckg = ckg = Diff()
    ckp = DiffClkParams(
        period=4 * n, delay=125 * p, vc=1350 * m, vd=900 * m, trf=800 * p
    )
    tb.ckgen = DiffClkGen(ckp)(ck=ckg, VSS=tb.VSS)

    # CML buffer the input clock, bring it into our CML levels
    tb.bufbias = bufbias = h.Signal()
    tb.iibuf = Idc(Idc.Params(dc=-1 * params.cml.ib))(p=bufbias, n=tb.VSS)
    tb.ckd = ckd = Diff()
    tb.ckbuf = CmlBuf(params.cml)(i=ckg, o=ckd, ibias=bufbias, VDD=tb.VDD, VSS=tb.VSS)

    # Differential Output
    tb.out = out = Diff()

    # Bias Generation
    tb.ibias = ibias = h.Signal()
    tb.ii = Idc(Idc.Params(dc=-1 * params.cml.ib))(p=ibias, n=tb.VSS)

    # Create the parameterized DUT
    tb.dut = CmlPulseGen(params.cml)(
        inp=ckd,
        out=tb.out,
        ibias=ibias,
        VDD=tb.VDD,
        VSS=tb.VSS,
    )
    return tb


def test_cml_pulsegen():
    """CML Divider Test(s)"""

    params = TbParams(pvt=Pvt(), cml=CmlParams(rl=4 * K, cl=25 * f, ib=250 * µ))
    sim = Sim(tb=CmlPulseGenTb(params), attrs=s130.install.include(params.pvt.p))
    sim.tran(tstop=12 * n)
    results = sim.run(sim_options)
    print(results)
