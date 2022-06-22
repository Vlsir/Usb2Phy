""" 
USB 2.0 Phy Custom / Analog Tests 
"""

# Std-Lib Imports
from pathlib import Path

import sitepdks as _
import s130
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.sim import Sim
from vlsirtools.spice import SimOptions, SupportedSimulators, ResultFormat

# DUT Imports
from . import PhaseInterp
from .. import QuadClock

# Widely re-used `SimOptions`
sim_options = SimOptions(
    rundir=Path("./scratch"),
    fmt=ResultFormat.SIM_DATA,
    simulator=SupportedSimulators.SPECTRE,
)


def test_phase_interp():
    """ Phase Interpolator Test(s) """

    from hdl21.primitives import Vpulse, Vdc

    @h.paramclass
    class QclkParams:
        """ Quadrature Clock Generator Parameters """

        period = h.Param(dtype=h.Prefixed, desc="Period")
        delay = h.Param(dtype=h.Prefixed, desc="Delay")
        v1 = h.Param(dtype=h.Prefixed, desc="Low Voltage Level")
        v2 = h.Param(dtype=h.Prefixed, desc="High Voltage Level")
        trf = h.Param(dtype=h.Prefixed, desc="Rise / Fall Time")

    @h.generator
    def QuadClockGen(p: QclkParams) -> h.Module:
        """ # Quadrature Clock Generator 
        For simulation, from ideal pulse voltage sources """

        def phpars(idx: int) -> Vpulse.Params:
            """ Closure to create the delay-value for quadrature index `idx`, valued 0-3. 
            Transitions start at 1/8 of a period, so that clocks are stable during time zero. """

            # Delays per phase, in eights of a period.
            # Note the negative values set `val2` as active during simulation time zero.
            vals = [1, 3, -3, -1]
            if idx < 0 or idx > 3:
                raise ValueError

            return Vpulse.Params(
                v1=p.v1,
                v2=p.v2,
                period=p.period,
                rise=p.trf,
                fall=p.trf,
                width=p.period / 2 - p.trf,
                delay=vals[idx] * p.period / 8 - p.trf / 2,
            )

        ckg = h.Module()
        ckg.VSS = VSS = h.Port()

        ckg.ckq = ckq = QuadClock(
            role=QuadClock.Roles.SINK, port=True, desc="Quadrature Clock Output"
        )
        ckg.v0 = Vpulse(phpars(0))(p=ckq.ck0, n=VSS)
        ckg.v90 = Vpulse(phpars(1))(p=ckq.ck90, n=VSS)
        ckg.v180 = Vpulse(phpars(2))(p=ckq.ck180, n=VSS)
        ckg.v270 = Vpulse(phpars(3))(p=ckq.ck270, n=VSS)
        return ckg

    from hdl21.prefix import m, p, n

    tb = h.sim.tb("PhaseInterpTb")
    tb.ckq = ckq = QuadClock()
    ckp = QclkParams(period=2 * n, delay=0 * p, v1=0 * m, v2=1800 * m, trf=100 * p)
    tb.ckgen = QuadClockGen(ckp)(ckq=ckq, VSS=tb.VSS)

    tb.VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=1800 * m))(p=tb.VDD, n=tb.VSS)

    tb.sel = h.Signal(width=5)
    tb.dck = h.Signal(width=1)
    tb.dut = PhaseInterp(nbits=5)(
        VDD=tb.VDD, VSS=tb.VSS, ckq=tb.ckq, sel=tb.sel, out=tb.dck
    )

    sim = Sim(tb=tb, attrs=s130.install.include(Corner.TYP))
    sim.include("scs130lp.sp")  # FIXME! relies on this netlist of logic cells
    sim.tran(tstop=50 * n, name="FOR_GODS_SAKE_MAKE_NO_NAME_WORK")
    results = sim.run(sim_options)
    print(results)
