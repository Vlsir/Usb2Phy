"""
# CML Ring Oscillator
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21.primitives import Res, Cap, Vdc
from hdl21.prefix import m
import s130
from s130 import MosParams

# Local Imports
from ..cmlparams import CmlParams
from ..width import Width


Nmos = s130.modules.nmos
NmosLvt = s130.modules.nmos_lvt
Pmos = s130.modules.pmos

# Define a few reused device-parameter combos
Pswitch = Pmos(MosParams(m=10))
Pbias = Pmos(MosParams(w=1, l=1, m=100))
Nswitch = NmosLvt(MosParams(m=10))
Nload = Nmos(MosParams(w=1, l=1, m=10))
Nbias = NmosLvt(MosParams(w=1, l=1, m=100))


@h.generator
def NmosCmlStage(params: CmlParams) -> h.Module:
    """# CML Delay Buffer"""

    Rl = Res(Res.Params(r=params.rl))
    Cl = Cap(Cap.Params(c=params.cl))

    @h.module
    class NmosCmlStage:
        # IO Interface
        VDD, VSS = h.Ports(2)

        ## Differential Input & Output
        i = h.Diff(port=True, role=h.Diff.Roles.SINK)
        o = h.Diff(port=True, role=h.Diff.Roles.SOURCE)

        ## Gate Bias for Current Sources
        bias = h.Input()

        # Internal Implementation
        ## Current Bias
        ni = Nbias(g=bias, s=VSS, b=VSS)
        ## Input Pair
        ns = h.Pair(Nswitch)(s=ni.d, g=i, d=h.inverse(o), b=VSS)
        ## Load Resistors
        rl = h.Pair(Rl)(p=o, n=VDD)
        ## Load Caps
        cl = h.Pair(Cl)(p=o, n=VDD)

    return NmosCmlStage


@h.generator
def PmosCmlStage(params: CmlParams) -> h.Module:
    """# Pmos Input Cml Stage"""

    Cl = Cap(Cap.Params(c=params.cl))

    @h.module
    class PmosCmlStage:
        # IO Interface
        VDD, VSS = h.Ports(2)

        ## Differential Input & Output
        i = h.Diff(port=True, role=h.Diff.Roles.SINK)
        o = h.Diff(port=True, role=h.Diff.Roles.SOURCE)

        ## Gate Bias for Current Sources
        pbias = h.Input()
        nbias = h.Port()

        # Internal Implementation
        ## Current Bias
        pi = Pbias(g=pbias, s=VDD, b=VDD)
        ## Input Pair
        ps = h.Pair(Pbias)(s=pi.d, g=i, d=h.inverse(o), b=VDD)
        ## Load Nmos
        nl = h.Pair(Nload)(d=o, g=nbias, s=VSS, b=VSS)
        ## Load Caps
        cl = h.Pair(Cl)(p=o, n=VSS)

    return PmosCmlStage


@h.generator
def BiasStage(params: CmlParams) -> h.Module:
    """ "Dummy" Stage for Gnerating Nmos Load Bias
    Same as the normal stages, but with 2x the current, and producing the `nbias` output."""

    Cl = Cap(Cap.Params(c=params.cl))

    @h.module
    class BiasStage:
        # IO Interface
        VDD, VSS = h.Ports(2)
        pbias, swing = h.Inputs(2)
        nbias = h.Output()

        # Internal Implementation
        fb = h.Signal()
        ## Current Bias
        pi = 2 * Pbias(g=pbias, s=VDD, b=VDD)
        ## Input Pair
        prf = Pswitch(s=pi.d, g=swing, d=nbias, b=VDD)
        pfb = Pswitch(s=pi.d, g=fb, d=fb, b=VDD)
        ## Load Nmos
        ndi = Nload(d=nbias, g=nbias, s=VSS, b=VSS)
        nld = Nload(d=fb, g=nbias, s=VSS, b=VSS)

    return BiasStage


@h.generator
def CmlRo(params: CmlParams) -> h.Module:
    """# CML Ring Oscillator"""

    @h.module
    class CmlRo:
        # IO Interface
        VDD, VSS = h.Ports(2)
        ## Bias input and gate
        pbias = h.Input(desc="Pmos Current Bias Input")

        # Internal Implementation
        nbias = h.Signal(desc="Nmos Gate Bias")

        stg0 = h.Diff(port=True, role=h.Diff.Roles.SOURCE)
        stg1 = h.Diff(port=True, role=h.Diff.Roles.SOURCE)
        stg2 = h.Diff(port=True, role=h.Diff.Roles.SOURCE)
        stg3 = h.Diff(port=True, role=h.Diff.Roles.SOURCE)

        ## Delay Stages
        i0 = PmosCmlStage(params)(
            i=stg0, o=stg1, pbias=pbias, nbias=nbias, VDD=VDD, VSS=VSS
        )
        i1 = PmosCmlStage(params)(
            i=stg1, o=stg2, pbias=pbias, nbias=nbias, VDD=VDD, VSS=VSS
        )
        i2 = PmosCmlStage(params)(
            i=stg2, o=stg3, pbias=pbias, nbias=nbias, VDD=VDD, VSS=VSS
        )
        i3 = PmosCmlStage(params)(
            i=stg3, o=h.inverse(stg0), pbias=pbias, nbias=nbias, VDD=VDD, VSS=VSS
        )

        ## Nmos Bias Generaor Stage
        swing = h.Signal(desc="Voltage Swing Reference, will become an input")
        vdc_swing = Vdc(Vdc.Params(dc=250 * m))(p=swing, n=VSS)
        bias_stage = BiasStage(params)(
            swing=swing, pbias=pbias, nbias=nbias, VDD=VDD, VSS=VSS
        )

        ## Current-Bias Diode Transistor
        pb = Pbias(g=pbias, d=pbias, s=VDD, b=VDD)

    return CmlRo


@h.generator
def Idac(_: h.HasNoParams) -> h.Module:
    """# Current Dac"""

    Nswitch = NmosLvt(MosParams(m=4))
    Nbias = NmosLvt(MosParams(w=1, l=1, m=1))  # ~ 0.3µA

    @h.module
    class IdacUnit:
        """Dac Unit Current"""

        # IO Interface
        VSS = h.Port()
        ## Primary I/O
        en = h.Input(desc="Unit Current Enable")
        out = h.Output(desc="Dac Output")
        ## Gate Bias
        bias = h.Input(desc="Current Bias Input")

        # Switch Nmos
        nsw = Nswitch(g=en, d=out, b=VSS)
        # Bias Nmos
        nb = Nbias(g=bias, d=nsw.s, s=VSS, b=VSS)

    @h.module
    class Idac:
        # IO Interface
        VDD, VSS = h.Ports(2)
        ## Primary I/O
        code = h.Input(width=5, desc="Dac Code")
        out = h.Output(desc="Dac Output")
        ## Bias input
        ibias = h.Input(desc="Current Bias Input")

        # Internal Implementation
        ## Diode Transistor, with Drain Switch
        udiode = 32 * IdacUnit(bias=ibias, out=ibias, en=VDD, VSS=VSS)
        ## Always-On Current Transistor
        uon = 64 * IdacUnit(bias=ibias, out=out, en=VDD, VSS=VSS)
        ## Primary Dac Units
        u0 = 1 * IdacUnit(bias=ibias, out=out, en=code[0], VSS=VSS)
        u1 = 2 * IdacUnit(bias=ibias, out=out, en=code[1], VSS=VSS)
        u2 = 4 * IdacUnit(bias=ibias, out=out, en=code[2], VSS=VSS)
        u3 = 8 * IdacUnit(bias=ibias, out=out, en=code[3], VSS=VSS)
        u4 = 16 * IdacUnit(bias=ibias, out=out, en=code[4], VSS=VSS)

    return Idac


@h.generator
def CmosEdgeDetector(params: Width) -> h.Module:
    """# Cmos Single-Ended Input Falling-Edge Detector"""

    from ..logiccells import Inv, Nor3
    from hdl21.generators import SeriesPar

    # Call the series-parallel generator to get a delay-chain worth of inverters
    DelayChain = SeriesPar(unit=Inv, series_conns=("i", "z"), nser=11, npar=1)

    @h.module
    class CmosEdgeDetector:
        # IO Interface
        VDD, VSS = h.Ports(2)
        ## Primary Input to be Edge-Detected
        inp = h.Input()
        ## Enable / Strength Input.
        ## Only bits of `out` which have `en` asserted are ever asserted.
        en = h.Input(width=params.width)
        out = h.Output(width=params.width)

        # Internal Implementation
        ## Delayed, Inverted Input Signal
        delayb = h.Signal()
        ## Delay Chain
        delay_chain = DelayChain(i=inp, z=delayb, VDD=VDD, VSS=VSS)

        ## Enable Inversions
        enb = h.Signal(width=params.width)
        eninvs = params.width * Inv()(i=en, z=enb, VDD=VDD, VSS=VSS)

        ## Edge detection logic: a bank of Nor3s
        nors = params.width * Nor3()(a=inp, b=delayb, c=enb, z=out, VDD=VDD, VSS=VSS)

    return CmosEdgeDetector


@h.generator
def CmosInjector(params: Width) -> h.Module:
    """# Cmos Injection Cell
    Just a binary-weighted bank of Nmos pull-down transistors"""

    Nswitch = NmosLvt(MosParams(m=4))

    @h.module
    class CmosInjector:
        # IO Interface
        VDD, VSS = h.Ports(2)
        inp = h.Input(width=params.width)
        out = h.Output(width=1)

    C = CmosInjector  # Give us a short name for all these references
    for bit in range(params.width):
        # Create a 2^bit wide switch, and add it to Module `CmosInjector`
        nsw = (2**bit) * Nswitch(g=C.inp[bit], d=C.out, s=C.VSS, b=C.VSS)
        C.add(name=f"nsw{bit}", val=nsw)

    return CmosInjector


@h.generator
def CmlIlDco(params: CmlParams) -> h.Module:
    """# CML Injection-Locked, Digitally Controlled Oscillator"""

    @h.module
    class CmlIlDco:
        # IO Interface
        VDD, VSS = h.Ports(2)
        ## Bias input and gate
        ibias = h.Input(desc="Current Bias Input, Nmos-Side")
        ## Frequency Code and Phase Injection
        fctrl = h.Input(width=5, desc="Frequency Control Code")
        refclk = h.Input(desc="Reference Clock Input")

        ## Oscillator Outputs
        stg0 = h.Diff(port=True, role=h.Diff.Roles.SOURCE)
        stg1 = h.Diff(port=True, role=h.Diff.Roles.SOURCE)
        stg2 = h.Diff(port=True, role=h.Diff.Roles.SOURCE)
        stg3 = h.Diff(port=True, role=h.Diff.Roles.SOURCE)

        # Internal Implementation
        ## Current-Bias Diode Pmos
        pbias = h.Signal(desc="Pmos Gate Bias, Output of Current Dac")
        pb = Pbias(g=pbias, d=pbias, s=VDD, b=VDD)

        ## Frequency-Control Current Dac
        idac = Idac()(ibias=ibias, code=fctrl, out=pbias, VDD=VDD, VSS=VSS)

        ## Core Ring Oscillator
        ro = CmlRo(params)(
            stg0=stg0, stg1=stg1, stg2=stg2, stg3=stg3, pbias=pbias, VDD=VDD, VSS=VSS
        )

        ## Injection
        _injection_strength = h.Concat(VSS, VSS, VDD)
        _off = h.Concat(VSS, VSS, VSS)
        edet = CmosEdgeDetector(width=3)(
            inp=refclk, en=_injection_strength, VDD=VDD, VSS=VSS
        )
        ninj = 3 * Nswitch(g=edet.out, d=stg0.p, s=stg0.n, b=VSS)
        # inj0p = CmosInjector(width=3)(inp=edet.out, out=stg0.p, VDD=VDD, VSS=VSS)
        # inj0n = CmosInjector(width=3)(inp=_off, out=stg0.n, VDD=VDD, VSS=VSS)
        # inj1p = CmosInjector(width=3)(inp=edet.out, out=stg1.p, VDD=VDD, VSS=VSS)
        # inj1n = CmosInjector(width=3)(inp=_off, out=stg1.n, VDD=VDD, VSS=VSS)
        # inj2p = CmosInjector(width=3)(inp=edet.out, out=stg2.p, VDD=VDD, VSS=VSS)
        # inj2n = CmosInjector(width=3)(inp=_off, out=stg2.n, VDD=VDD, VSS=VSS)
        # inj3p = CmosInjector(width=3)(inp=edet.out, out=stg3.p, VDD=VDD, VSS=VSS)
        # inj3n = CmosInjector(width=3)(inp=_off, out=stg3.n, VDD=VDD, VSS=VSS)

    return CmlIlDco
