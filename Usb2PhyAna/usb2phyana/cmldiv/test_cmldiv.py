"""
# CML Divider 
## Unit Tests
"""

import io

# Hdl & PDK Imports
import sitepdks as _
import s130
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.sim import Sim
from hdl21.prefix import m, p, n, K, f, µ
from hdl21.primitives import Vdc, Idc

# DUT Imports
from .cmldiv import CmlDiv, CmlParams
from ..cmlbuf import CmlBuf
from ..diff import Diff
from ..tests.diffclockgen import DiffClkGen, DiffClkParams
from ..tests.sim_options import sim_options


@h.generator
def CmlDivTb(params: CmlParams) -> h.Module:
    """CML Divider Testbench"""

    tb = h.sim.tb("CmlDivTb")
    tb.ckg = ckg = Diff()
    tb.ckd = ckd = Diff()
    ckp = DiffClkParams(
        period=1 * n, delay=125 * p, vc=1350 * m, vd=900 * m, trf=200 * p
    )
    tb.ckgen = DiffClkGen(ckp)(ck=ckg, VSS=tb.VSS)

    tb.VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=1800 * m, ac=0 * m))(p=tb.VDD, n=tb.VSS)

    # CML buffer the input clock, bring it into our CML levels
    tb.bufbias = bufbias = h.Signal()
    tb.iibuf = Idc(Idc.Params(dc=-1 * params.ib))(p=bufbias, n=tb.VSS)
    tb.ckbuf = CmlBuf(params)(i=ckg, o=ckd, ibias=bufbias, VDD=tb.VDD, VSS=tb.VSS)

    tb.i = i = Diff()
    tb.q = q = Diff()
    tb.ibias = ibias = h.Signal()
    tb.ii = Idc(Idc.Params(dc=-1 * params.ib))(p=ibias, n=tb.VSS)

    # Create the parameterized DUT
    tb.dut = CmlDiv(params)(
        clk=ckd,
        q=q,
        i=i,
        ibias=ibias,
        VDD=tb.VDD,
        VSS=tb.VSS,
    )
    return tb


from ..tests.sim_test_mode import SimTestMode


def test_cml_div(simtestmode: SimTestMode):
    """CML Divider Test(s)"""

    if simtestmode == SimTestMode.NETLIST:
        params = CmlParams(rl=4 * K, cl=25 * f, ib=250 * µ)
        h.netlist(CmlDivTb(params), dest=io.StringIO())
    else:
        sim_cml_div()


def sim_cml_div():
    params = CmlParams(rl=4 * K, cl=25 * f, ib=250 * µ)
    sim = Sim(tb=CmlDivTb(params), attrs=s130.install.include(Corner.TYP))
    sim.tran(tstop=12 * n)
    results = sim.run(sim_options)
    print(results)
