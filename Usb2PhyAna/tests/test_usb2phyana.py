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
from usb2phyana import OneHotRotator, PhaseInterp, Usb2PhyAna, QuadClock

# Widely re-used `SimOptions`
sim_options = SimOptions(
    rundir=Path("./scratch"),
    fmt=ResultFormat.SIM_DATA,
    simulator=SupportedSimulators.SPECTRE,
)


def test_pdk():
    """ Non-PHY test that we can execute simulations with the installed PDK """

    from hdl21.prefix import µ, m
    from hdl21.primitives import Vdc

    @h.module
    class Tb:
        VSS = h.Port()  # The testbench interface: sole port VSS

        VDD = h.Signal()
        v = Vdc(Vdc.Params(dc=1800 * m))(p=VDD, n=VSS)

        nmos = s130.modules.nmos(s130.MosParams())(d=VDD, g=VDD, s=VSS, b=VSS)
        nmos_lvt = s130.modules.nmos_lvt(s130.MosParams())(d=VDD, g=VDD, s=VSS, b=VSS)
        pmos = s130.modules.pmos(s130.MosParams())(d=VSS, g=VSS, s=VDD, b=VDD)
        pmos_hvt = s130.modules.pmos_hvt(s130.MosParams())(d=VSS, g=VSS, s=VDD, b=VDD)

    sim = Sim(tb=Tb, attrs=s130.install.include(Corner.TYP))
    sim.tran(tstop=1 * µ, name="tran1")
    res = sim.run(sim_options)
    print(res)


def test_onehot_rotator():
    """ Simulate the `OneHotRotator` """

    def rotator_tb() -> h.Module:
        from hdl21.prefix import m, n, p, f
        from hdl21.primitives import Vdc, Vpulse, Cap

        # "Parameter" Width
        width = 16

        tb = h.sim.tb("OneHotRotatorTb")
        tb.VDD = h.Signal()
        tb.vvdd = Vdc(Vdc.Params(dc=1800 * m))(p=tb.VDD, n=tb.VSS)

        # Instantiate the rotator DUT
        tb.dut = OneHotRotator(width=width)(VDD=tb.VDD, VSS=tb.VSS)

        tb.cloads = width * Cap(Cap.Params(c=1 * f))(p=tb.dut.out, n=tb.VSS)

        tb.vsclk = Vpulse(
            Vpulse.Params(
                delay=0,
                v1=0,
                v2=1800 * m,
                period=2 * n,
                rise=1 * p,
                fall=1 * p,
                width=1 * n,
            )
        )(p=tb.dut.sclk, n=tb.VSS)
        tb.vrstn = Vpulse(
            Vpulse.Params(
                delay=9500 * p,
                v1=0,
                v2=1800 * m,
                period=2,
                rise=1 * p,
                fall=1 * p,
                width=1,
            )
        )(p=tb.dut.rstn, n=tb.VSS)

        return tb

    def rotator_sim() -> h.sim.Sim:
        from hdl21.prefix import n

        sim = h.sim.Sim(tb=rotator_tb(), attrs=s130.install.include(Corner.TYP))
        sim.tran(tstop=64 * n, name="THE_TRAN_DUH")
        return sim

    sim = rotator_sim()
    sim.include("scs130lp.sp")  # FIXME! relies on this netlist of logic cells
    results = sim.run(sim_options)

    print(results)


def test_phase_interp():
    """ Phase Interpolator Test(s) """

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

        from hdl21.primitives import Vpulse

        def pidx(idx: int) -> Vpulse.Params:
            """ Create the delay-value for quadrature index `idx`, valued 0-3. 
            Transitions start at 1/8 of a period, so that clocks are stable during time zero. """

            # Delays per phase, in eights of a period.
            # Note the negative values set `val2` as active during simulation time zero.
            vals = [1, 3, -3, -1]
            # vals = {0: 1, 1: 3, 2: -3, 3: -1}
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
        ckg.v0 = Vpulse(pidx(0))(p=ckq.ck0, n=VSS)
        ckg.v90 = Vpulse(pidx(1))(p=ckq.ck90, n=VSS)
        ckg.v180 = Vpulse(pidx(2))(p=ckq.ck180, n=VSS)
        ckg.v270 = Vpulse(pidx(3))(p=ckq.ck270, n=VSS)
        return ckg

    from hdl21.prefix import m, p, n

    tb = h.sim.tb("PhaseInterpTb")
    tb.ckq = ckq = QuadClock()
    ckp = QclkParams(period=2 * n, delay=0 * p, v1=0 * m, v2=1800 * m, trf=200 * p)
    tb.ckgen = QuadClockGen(ckp)(ckq=ckq, VSS=tb.VSS)
    # tb.dut = PhaseInterp(nbits=5)()

    sim = Sim(tb=tb)
    sim.tran(tstop=10 * n, name="FOR_GODS_SAKE")
    results = sim.run(sim_options)
    print(results)


def test_netlisting():
    """ Test netlisting some big-picture Modules """
    import sys

    # h.netlist(h.to_proto(Serdes(SerdesParams())), dest=sys.stdout)
    # h.netlist(h.to_proto(SerdesTxLane), dest=sys.stdout)
    # h.netlist(h.to_proto(SerdesRxLane), dest=sys.stdout)
    # h.netlist(h.to_proto(OneHotEncoder(width=10)), dest=sys.stdout)
    h.netlist(h.to_proto(Usb2PhyAna), dest=sys.stdout)
    h.netlist(h.to_proto(OneHotRotator(width=8)), dest=sys.stdout)
    h.netlist(h.to_proto(PhaseInterp()), dest=sys.stdout)

