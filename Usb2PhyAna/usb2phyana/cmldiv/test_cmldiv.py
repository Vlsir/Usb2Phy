"""
# CML Divider 
## Unit Tests
"""

# Std-Lib Imports
from pathlib import Path

import sitepdks as _
import s130
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.sim import Sim
from hdl21.prefix import m, p, n, K, f, µ
from hdl21.primitives import Vpulse, Vdc, Idc

# DUT Imports
from ..tests.sim_options import sim_options
from .cmldiv import CmlBuf, CmlDiv, CmlParams, Diff



@h.paramclass
class DiffClkParams:
    """ Differential Clock Generator Parameters """

    period = h.Param(dtype=h.Prefixed, desc="Period")
    delay = h.Param(dtype=h.Prefixed, desc="Delay")
    vd = h.Param(dtype=h.Prefixed, desc="Differential Voltage")
    vc = h.Param(dtype=h.Prefixed, desc="Common-Mode Voltage")
    trf = h.Param(dtype=h.Prefixed, desc="Rise / Fall Time")


@h.generator
def DiffClkGen(p: DiffClkParams) -> h.Module:
    """ # Differential Clock Generator 
    For simulation, from ideal pulse voltage sources """

    ckg = h.Module()
    ckg.VSS = VSS = h.Port()
    ckg.ck = ck = Diff(role=Diff.Roles.SINK, port=True)

    def vparams(polarity: bool) -> Vpulse.Params:
        """ Closure to create the pulse-source parameters for each differential half. 
        Argument `polarity` is True for positive half, False for negative half. """
        # Initially create the voltage levels for the positive half
        v1 = p.vc + p.vd / 2
        v2 = p.vc - p.vd / 2
        if not polarity:  # And for the negative half, swap them
            v1, v2 = v2, v1
        return Vpulse.Params(
            v1=v1,
            v2=v2,
            period=p.period,
            rise=p.trf,
            fall=p.trf,
            width=p.period / 2 - p.trf,
            delay=p.delay,
        )

    # Create the two complementary pulse-sources
    ckg.vp = Vpulse(vparams(True))(p=ck.p, n=VSS)
    ckg.vn = Vpulse(vparams(False))(p=ck.n, n=VSS)

    return ckg


@h.generator
def CmlDivTb(params: CmlParams) -> h.Module:
    """ CML Divider Testbench """

    tb = h.sim.tb("CmlDivTb")
    tb.ckg = ckg = Diff()
    tb.ckd = ckd = Diff()
    ckp = DiffClkParams(
        period=1 * n, delay=125 * p, vc=1350 * m, vd=900 * m, trf=200 * p
    )
    tb.ckgen = DiffClkGen(ckp)(ck=ckg, VSS=tb.VSS)

    tb.VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=1800 * m))(p=tb.VDD, n=tb.VSS)

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
        ckp=ckd.p,
        ckn=ckd.n,
        ip=i.p,
        in_=i.n,
        qp=q.p,
        qn=q.n,
        ibias=ibias,
        VDD=tb.VDD,
        VSS=tb.VSS,
    )
    return tb


def test_cml_div():
    """ CML Divider Test(s) """

    params = CmlParams(rl=4 * K, cl=25 * f, ib=250 * µ)
    sim = Sim(tb=CmlDivTb(params), attrs=s130.install.include(Corner.TYP))
    sim.tran(tstop=12 * n, name="FOR_GODS_SAKE_MAKE_NO_NAME_WORK")
    results = sim.run(sim_options)
    print(results)
