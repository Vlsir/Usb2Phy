""" 
# CML Phase Interpolator 
## Testbench & Unit Tests
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21.prefix import m, n, PICO, µ, f, K
from hdl21.primitives import Vdc, Idc

# DUT Imports
from .cmlpi import PhaseInterp
from .tb import TbParams 
from .. import Diff
from .. import QuadClock 
from ...cmlbuf import CmlBuf
from ...cmlparams import CmlParams
from ...tests.quadclockgen import QuadClockGen, QclkParams


@h.generator
def PhaseInterpTb(p: TbParams) -> h.Module:
    """ Phase Interpolator Testbench """

    params = CmlParams(rl=4 * K, cl=25 * f, ib=250 * µ)

    # Create our testbench 
    tb = h.sim.tb("PhaseInterpTb")
    # Generate and drive VDD
    tb.VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=p.VDD))(p=tb.VDD, n=tb.VSS)

    # Generate the input quadrature clock
    tb.ckq = ckq = QuadClock()
    qckparams = QclkParams(v1=0 * m, v2=p.VDD, period=2 * n, trf=100 * PICO)
    tb.ckgen = QuadClockGen(qckparams)(ckq=ckq, VSS=tb.VSS)

    # Buffer both input clocks, pulling them into our CML levels
    tb.ckibuf = Diff()
    tb.ckqbuf = Diff()

    tb.bufbiasi = bufbiasi = h.Signal()
    tb.iibuf = Idc(Idc.Params(dc=-1 * params.ib))(p=bufbiasi, n=tb.VSS)
    tb.ckbufi = CmlBuf(params)(
        i=h.AnonymousBundle(p=tb.ckq.ck0, n=tb.ckq.ck180),
        o=tb.ckibuf,
        ibias=bufbiasi,
        VDD=tb.VDD,
        VSS=tb.VSS,
    )

    tb.bufbiasq = bufbiasq = h.Signal()
    tb.iqbuf = Idc(Idc.Params(dc=-1 * params.ib))(p=bufbiasq, n=tb.VSS)
    tb.ckbufq = CmlBuf(params)(
        i=h.AnonymousBundle(p=tb.ckq.ck90, n=tb.ckq.ck270),
        o=tb.ckqbuf,
        ibias=bufbiasq,
        VDD=tb.VDD,
        VSS=tb.VSS,
    )

    # Set up the select/ code input
    tb.code = h.Signal(width=5)

    def vbit(i: int):
        """ Create a `Vdc` call equal to either `p.VDD` or zero. """
        val = p.VDD if i else 0 * m
        return Vdc(Vdc.Params(dc=val))

    def vcode(code: int) -> None:
        """ Closure to drive `tb.code` to the (binary) value of `code`. 
        Essentially an integer to binary, and then binary to `Vdc.Params` converter. """

        if code < 0:
            raise ValueError

        # Convert to a binary-valued string
        bits = bin(code)[2:].zfill(tb.code.width)

        # And create a voltage source for each bit
        for idx in range(5):
            bitval = int(bits[-(idx + 1)])
            vinst = vbit(bitval)(p=tb.code[idx], n=tb.VSS)
            tb.add(name=f"vcode{idx}", val=vinst)

    # Call all that to drive the code bus
    vcode(p.code)

    tb.dck = Diff()
    ckqbuf = h.AnonymousBundle(
        ck0=tb.ckibuf.p, ck90=tb.ckqbuf.p, ck180=tb.ckibuf.n, ck270=tb.ckqbuf.n,
    )
    tb.dut = PhaseInterp(nbits=5)(
        VDD=tb.VDD, VSS=tb.VSS, ckq=ckqbuf, sel=tb.code, out=tb.dck
    )
    return tb


def test_phase_interp():
    """ Phase Interpolator Test(s) """

    from .tb import sim 
    from .compare import save_plot

    params = [TbParams(code=code) for code in range(32)]
    delays = [sim(tb=PhaseInterpTb(p), params=p) for p in params]
    print(delays)
    save_plot(delays, "CML PI", "cmlpi.png")
