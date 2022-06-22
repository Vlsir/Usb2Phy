""" 
USB 2.0 Phy Custom / Analog
"""

# Std-Lib Imports
from typing import Dict
from enum import Enum, auto

# Hdl & PDK Imports
import hdl21 as h


@h.bundle
class Diff:
    """ Differential Bundle """

    class Roles(Enum):
        SOURCE = auto()
        SINK = auto()

    p, n = h.Signals(2, src=Roles.SOURCE, dest=Roles.SINK)


@h.bundle
class QuadClock:
    """ # Quadrature Clock Bundle 
    Includes four 90-degree-separated phases. """

    class Roles(Enum):
        # Clock roles: source or sink
        SOURCE = auto()
        SINK = auto()

    # The four quadrature phases, all driven by SOURCE and consumed by SINK.
    ck0, ck90, ck180, ck270 = h.Signals(4, src=Roles.SOURCE, dest=Roles.SINK)


@h.paramclass
class Width:
    """ Parameter class for Generators with a single integer-valued `width` parameter. """

    width = h.Param(dtype=int, desc="Parametric Width", default=1)


""" 
# Generic Wrappers 
"""


def wrap(wrapper_name: str, wrapped_name: str, ports: Dict[str, str]) -> h.Module:
    """ Wrap a foundry cell, creating an `ExternalModule` for it and a wrapper `Module` named `wrapper_name`. """

    m = h.Module(name=wrapper_name)
    m.VDD, m.VSS = h.Ports(2)
    for p in ports.keys():
        m.add(h.Port(), name=p)

    # Create a wrapper `ExternalModule`
    Inner = h.ExternalModule(
        name=wrapped_name,
        port_list=[
            h.Port(name=n) for n in list(ports.values()) + "vgnd vnb vpb vpwr".split()
        ],
        desc=f"PDK {wrapped_name}",
    )
    # Create its connections dictionary
    conns = {inner: getattr(m, outer) for outer, inner in ports.items()}
    # Add the power and ground connections
    conns["vgnd"] = conns["vnb"] = m.VSS
    conns["vpwr"] = conns["vpb"] = m.VDD

    # Create an Instance of the inner `ExternalModule`
    m.i = Inner()(**conns)

    # Return the wrapper module
    return m


# Wrapped Foundry / PDK Cells
Inv = wrap("Inv", "scs130lp_inv_2", ports={"i": "A", "z": "Y"})
Or2 = wrap("Or2", "scs130lp_or2_1", ports={"a": "A", "b": "B", "z": "X"})
Or3 = wrap("Or3", "scs130lp_or3_1", ports={"a": "A", "b": "B", "c": "C", "z": "X"})
And2 = wrap("And2", "scs130lp_and2_1", ports={"a": "A", "b": "B", "z": "X"})
And3 = wrap("And3", "scs130lp_and3_1", ports={"a": "A", "b": "B", "c": "C", "z": "X"})
FlopResetLow = wrap(
    "FlopResetLow",
    "scs130lp_dfrtp_4",
    {"clk": "CLK", "d": "D", "q": "Q", "rstn": "RESETB"},
)
FlopResetHigh = wrap(
    "FlopResetHigh",
    "scs130lp_dfstp_4",
    {"clk": "CLK", "d": "D", "q": "Q", "rstn": "SETB"},
)

"""
Generic External Modules 
"""

Flop = h.ExternalModule(
    name="Flop",
    port_list=[
        h.Input(name="d"),
        h.Input(name="clk"),
        h.Output(name="q"),
        h.Port(name="VDD"),
        h.Port(name="VSS"),
    ],
    desc="Generic Rising-Edge D Flip Flop",
)
Latch = h.ExternalModule(
    name="Latch",
    port_list=[
        h.Input(name="d"),
        h.Input(name="clk"),
        h.Output(name="q"),
        h.Port(name="VDD"),
        h.Port(name="VSS"),
    ],
    desc="Generic Active High Level-Sensitive Latch",
)


@h.paramclass
class WeightInvParams:
    weight = h.Param(dtype=int, desc="Weight")


@h.generator
def WeightInv(p: WeightInvParams) -> h.Module:
    import s130
    from s130 import MosParams

    nmos = s130.modules.nmos
    pmos = s130.modules.pmos

    m = h.Module()
    m.VDD, m.VSS = h.Ports(2)
    m.i = h.Input()
    m.z = h.Output()
    m.n = nmos(MosParams(w=1, m=p.weight))(d=m.z, g=m.i, s=m.VSS, b=m.VSS)
    m.p = pmos(MosParams(w=2, m=p.weight))(d=m.z, g=m.i, s=m.VDD, b=m.VDD)

    return m


@h.generator
def TriInv(p: Width) -> h.Module:
    import s130
    from s130 import MosParams

    nmos = s130.modules.nmos
    pmos = s130.modules.pmos

    m = h.Module()
    m.VDD, m.VSS = h.Ports(2)
    m.i, m.en = h.Inputs(2)
    m.z = h.Output()
    m.enb = h.Signal()

    # Enable inversion inverter
    m.pinv = pmos(MosParams(w=1, m=1))(d=m.enb, g=m.en, s=m.VDD, b=m.VDD)
    m.ninv = nmos(MosParams(w=1, m=1))(d=m.enb, g=m.en, s=m.VSS, b=m.VSS)

    # Main Tristate Inverter
    m.pi = pmos(MosParams(w=2, m=p.width))(g=m.i, s=m.VDD, b=m.VDD)
    m.pe = pmos(MosParams(w=2, m=p.width))(d=m.z, g=m.enb, s=m.pi.d, b=m.VDD)
    m.ne = nmos(MosParams(w=1, m=p.width))(d=m.z, g=m.en, b=m.VSS)
    m.ni = nmos(MosParams(w=1, m=p.width))(d=m.ne.s, g=m.i, s=m.VSS, b=m.VSS)

    return m


@h.paramclass
class PhaseWeighterParams:
    wta = h.Param(dtype=int, desc="Weight of Input A")
    wtb = h.Param(dtype=int, desc="Weight of Input B")


@h.generator
def PhaseWeighter(p: PhaseWeighterParams) -> h.Module:
    """ # Phase-Weighter
    Drives a single output with two out-of-phase inputs `a` and `b`, 
    with weights dictates by params `wta` and `wtb`. """

    @h.module
    class PhaseWeighter:
        # IO Ports
        VDD, VSS = h.Ports(2)
        a, b = h.Inputs(2)
        out = h.Output()
        mix = h.Signal(desc="Internal phase-mixing node")

    # Give it a shorthand name for these manipulations
    P = PhaseWeighter

    if p.wta > 0:  # a-input inverter
        P.inva = WeightInv(WeightInvParams(weight=p.wta))(
            i=P.a, z=P.mix, VDD=P.VDD, VSS=P.VSS
        )
    if p.wtb > 0:  # b-input inverter
        P.invb = WeightInv(WeightInvParams(weight=p.wtb))(
            i=P.b, z=P.mix, VDD=P.VDD, VSS=P.VSS
        )

    # Output inverter, with the combined size of the two inputs
    P.invo = WeightInv(WeightInvParams(weight=1))(
        i=P.mix, z=P.out, VDD=P.VDD, VSS=P.VSS
    )

    return PhaseWeighter


@h.paramclass
class PiParams:
    """ Phase Interpolator Parameters """

    nbits = h.Param(dtype=int, default=5, desc="Resolution, or width of select-input.")


@h.generator
def PhaseGenerator(p: PiParams) -> h.Module:
    """ # Phase Generator (Generator) (Get it?) 
    
    Takes a primary input `QuadClock` and interpolates to produce 
    an array of equally-spaced output phases. """

    PhaseGen = h.Module()
    VDD, VSS = PhaseGen.VDD, PhaseGen.VSS = h.Ports(2)
    ckq = PhaseGen.ckq = QuadClock(
        role=QuadClock.Roles.SINK, port=True, desc="Quadrature input"
    )
    phases = PhaseGen.phases = h.Output(
        width=2 ** p.nbits, desc="Array of equally-spaced phases"
    )

    if p.nbits != 5:
        msg = f"Yeah we know that's a parameter, but this is actually hard-coded to 5 bits for now"
        raise ValueError(msg)

    # Generate a set of PhaseWeighters and output phases for each pair of quadrature inputs
    for wtb in range(8):
        p = PhaseWeighterParams(wta=8 - wtb, wtb=wtb)
        index = wtb
        PhaseGen.add(
            name=f"weight{index}",
            val=PhaseWeighter(p)(
                a=ckq.ck0, b=ckq.ck90, out=phases[index], VDD=VDD, VSS=VSS
            ),
        )
    for wtb in range(8):
        p = PhaseWeighterParams(wta=8 - wtb, wtb=wtb)
        index = 8 + wtb
        PhaseGen.add(
            name=f"weight{index}",
            val=PhaseWeighter(p)(
                a=ckq.ck90, b=ckq.ck180, out=phases[index], VDD=VDD, VSS=VSS
            ),
        )
    for wtb in range(8):
        p = PhaseWeighterParams(wta=8 - wtb, wtb=wtb)
        index = 16 + wtb
        PhaseGen.add(
            name=f"weight{index}",
            val=PhaseWeighter(p)(
                a=ckq.ck180, b=ckq.ck270, out=phases[index], VDD=VDD, VSS=VSS
            ),
        )
    for wtb in range(8):
        p = PhaseWeighterParams(wta=8 - wtb, wtb=wtb)
        index = 24 + wtb
        PhaseGen.add(
            name=f"weight{index}",
            val=PhaseWeighter(p)(
                a=ckq.ck270, b=ckq.ck0, out=phases[index], VDD=VDD, VSS=VSS
            ),
        )

    return PhaseGen


@h.generator
def PhaseSelector(p: PiParams) -> h.Module:
    """ # Phase Selector Mux """

    @h.module
    class PhaseSelector:
        # IO Interface
        VDD, VSS = h.Ports(2)
        phases = h.Input(width=2 ** p.nbits, desc="Array of equally-spaced phases")
        sel = h.Input(width=p.nbits, desc="Selection input")
        out = h.Output(width=1, desc="Clock output")

        # Internal Contents
        encoder = OneHotEncoder(width=5)(bin=sel, en=VDD, VDD=VDD, VSS=VSS)
        invs = 32 * TriInv(width=4)(i=phases, en=encoder.out, z=out, VDD=VDD, VSS=VSS)

    return PhaseSelector


@h.generator
def PhaseInterp(p: PiParams) -> h.Module:
    """ Phase Interpolator Generator """

    @h.module
    class PhaseInterp:
        # IO Interface
        VDD, VSS = h.Ports(2)
        ckq = QuadClock(role=QuadClock.Roles.SINK, port=True, desc="Quadrature input")
        sel = h.Input(width=p.nbits, desc="Selection input")
        out = h.Output(width=1, desc="Clock output")

        # Internal Signals
        phases = h.Signal(width=2 ** p.nbits, desc="Array of equally-spaced phases")

        # Instantiate the phase-generator and phase-selector
        phgen = PhaseGenerator(p)(ckq=ckq, phases=phases, VDD=VDD, VSS=VSS)
        phsel = PhaseSelector(p)(phases=phases, sel=sel, out=out, VDD=VDD, VSS=VSS)

    return PhaseInterp


@h.module
class OneHotEncoder2to4:
    """ 
    # One-Hot Encoder
    2b to 4b with enable. 
    Also serves as the base-case for the recursive `OneHotEncoder` generator. 
    All outputs are low if enable-input `en` is low. 
    """

    # IO Interface
    VDD, VSS = h.Ports(2)
    en = h.Input(width=1, desc="Enable input. Active high.")
    bin = h.Input(width=2, desc="Binary valued input")
    out = h.Output(width=4, desc="One-hot encoded output")

    # Internal Contents
    # Input inverters
    binb = h.Signal(width=2, desc="Inverted binary input")
    invs = 2 * Inv()(i=bin, z=binb, VDD=VDD, VSS=VSS)

    # The primary logic: a set of four And3's
    ands = 4 * And3()(
        a=h.Concat(binb[0], bin[0], binb[0], bin[0]),
        b=h.Concat(binb[1], binb[1], bin[1], bin[1]),
        c=en,
        z=out,
        VDD=VDD,
        VSS=VSS,
    )


@h.module
class OneHotEncoder3to8:
    """ 
    # One-Hot Encoder
    3b to 8b with enable. 
    Also serves as a base-case for the recursive `OneHotEncoder` generator, 
    for cases with an odd initial width. Uses the `2to4` version internally. 
    All outputs are low if enable-input `en` is low. 
    """

    # IO Interface
    VDD, VSS = h.Ports(2)
    en = h.Input(width=1, desc="Enable input. Active high.")
    bin = h.Input(width=3, desc="Binary valued input")
    out = h.Output(width=8, desc="One-hot encoded output")

    # Internal Contents
    inv = Inv()(i=bin[2], VDD=VDD, VSS=VSS)
    and0 = And2(a=inv.z, b=en, VDD=VDD, VSS=VSS)
    and1 = And2(a=bin[2], b=en, VDD=VDD, VSS=VSS)

    # Two LSB 2->4b Encoders
    lsbs0 = OneHotEncoder2to4(en=and0.z, bin=bin[0:2], out=out[0:4], VDD=VDD, VSS=VSS)
    lsbs1 = OneHotEncoder2to4(en=and1.z, bin=bin[0:2], out=out[4:8], VDD=VDD, VSS=VSS)


@h.generator
def OneHotEncoder(p: Width) -> h.Module:
    """ 
    # One-Hot Encoder Generator 
    Recursively creates a `p.width`-bit one-hot encoder Module comprised of `OneHotEncoder2to4`s. 
    Also generates `OneHotEncoder` Modules for `p.width-2`, `p.width-4`, et al, down to 
    the base case two to four bit Module. 
    """

    if p.width < 2:
        raise ValueError(f"OneHotEncoder {p} width must be > 1")
    if p.width == 2:  # Base case: the 2 to 4b encoder
        return OneHotEncoder2to4
    if p.width == 3:  # Base case: the 3 to 8b encoder
        return OneHotEncoder3to8

    # Recursive case. Generate from `width-2` children.
    m = h.Module()
    m.VDD, m.VSS = h.Ports(2)
    m.en = h.Input(width=1, desc="Enable input. Active high.")
    m.bin = h.Input(width=p.width, desc="Binary valued input")
    m.out = h.Output(width=2 ** p.width, desc="One-hot encoded output")

    # Thermo-encode the two MSBs, creating select signals for the LSBs
    m.lsb_sel = h.Signal(width=4)
    m.msb_encoder = OneHotEncoder2to4(
        en=m.en, bin=m.bin[-2:], out=m.lsb_sel, VDD=m.VDD, VSS=m.VSS
    )

    # Peel off two bits and recursively generate our child encoder Module
    child = OneHotEncoder(width=p.width - 2)
    # And create four instances of it, enabled by the thermo-decoded MSBs
    m.children = 4 * child(
        en=m.lsb_sel, bin=m.bin[:-2], out=m.out, VDD=m.VDD, VSS=m.VSS
    )

    return m


@h.module
class ThermoEncoder3to8:
    """ 
    # Thermometer Encoder
    3b to 8b with enable. Internally uses `OneHot3to8`. 
    """

    # IO Interface
    VDD, VSS = h.Ports(2)
    en = h.Input(width=1, desc="Enable input. Active high.")
    bin = h.Input(width=3, desc="Binary valued input")
    out = h.Output(width=8, desc="Thermometer encoded output")

    # Internal Contents
    onehot = h.Signal(width=8, desc="Internal one-hot encoded value")
    bin2onehot = OneHotEncoder3to8(en=en, bin=bin, out=onehot, VDD=VDD, VSS=VSS)

    # Conversion from one-hot to thermometer
    ors = 8 * Or2(a=onehot, b=h.Concat(out[1:], VSS), z=out, VDD=VDD, VSS=VSS)


@h.generator
def OneHotMux(p: Width) -> h.Module:
    """ # One-Hot Selected Mux 
    Selection input is one-hot encoded. Any conversion is to be done externally. """

    m = h.Module()

    # IO Interface
    m.VDD, m.VSS = h.Ports(2)
    m.inp = h.Input(width=p.width, desc="Primary Input")
    m.sel = h.Input(width=p.width, desc="One-Hot Encoded Selection Input")
    m.out = h.Output(width=1)

    # Internal Implementation
    # Flat bank of `width` tristate inverters
    m.invs = p.width * TriInv()(i=m.inp, en=m.sel, z=m.out, VDD=m.VDD, VSS=m.VSS)
    return m


@h.generator
def Counter(p: Width) -> h.Module:
    """ # Binary Counter Generator """

    m = h.Module()
    m.VDD, m.VSS = h.Ports(2)
    m.clk = h.Input(desc="Primary input. Increments state on each rising edge.")
    m.out = h.Output(width=p.width, desc="Counterer Output State")

    # Divide-by-two stages
    m.invs = p.width * Inv()(i=m.out, VDD=m.VDD, VSS=m.VSS)
    m.flops = p.width * Flop()(d=m.invs.z, q=m.out, clk=m.clk, VDD=m.VDD, VSS=m.VSS)
    return m


@h.generator
def OneHotRotator(p: Width) -> h.Module:
    """ # One Hot Rotator 
    A set of `p.width` flops with a one-hot state, which rotates by one bit on each clock cycle. 
    When active-low reset-input `rstn` is asserted, the LSB is enabled. """

    m = h.Module()
    m.VDD, m.VSS = h.Ports(2)

    # IO Interface: Clock, Reset, and a `width`-bit One-Hot output
    m.sclk = h.Input(width=1, desc="Serial clock")
    m.rstn = h.Input(width=1, desc="Active-low reset")
    m.out = h.Output(width=p.width, desc="One-hot rotating output")

    # Internal signals for next-state and inverse-output
    m.outb = h.Signal(width=p.width, desc="Internal complementary outputs")
    m.nxt = h.Signal(width=p.width, desc="Next state; D pins of state flops")

    # The core logic: each next-bit is the AND of the prior bit, and the inverse of the current bit.
    m.out_invs = p.width * Inv()(i=m.out, z=m.outb, VDD=m.VDD, VSS=m.VSS)
    m.ands = p.width * And2()(
        a=m.outb, b=h.Concat(m.out[-1], m.out[0:-1]), z=m.nxt, VDD=m.VDD, VSS=m.VSS
    )
    # LSB flop, output asserted while in reset
    m.lsb_flop = FlopResetHigh()(
        d=m.nxt[0], clk=m.sclk, q=m.out[0], rstn=m.rstn, VDD=m.VDD, VSS=m.VSS
    )
    # All other flops, outputs de-asserted in reset
    m.flops = (p.width - 1) * FlopResetLow()(
        d=m.nxt[1:], clk=m.sclk, q=m.out[1:], rstn=m.rstn, VDD=m.VDD, VSS=m.VSS
    )

    return m


@h.generator
def TxSerializer(_: h.HasNoParams) -> h.Module:
    """ Transmit Serializer 
    Includes parallel-clock generation divider """

    m = h.Module()
    m.VDD, m.VSS = h.Ports(2)

    m.pdata = h.Input(width=16, desc="Parallel Input Data")
    m.sdata = h.Output(width=1, desc="Serial Output Data")
    m.pclk = h.Output(width=1, desc="*Output*, Divided Parallel Clock")
    m.sclk = h.Input(width=1, desc="Input Serial Clock")

    # Create the four-bit counter state, consisting of the parallel clock as MSB,
    # and three internal-signal LSBs.
    m.count_lsbs = h.Signal(width=3, desc="LSBs of Divider-Counterer")
    count = h.Concat(m.count_lsbs, m.pclk)

    m.counter = Counter(width=4)(clk=m.sclk, out=count, VDD=m.VDD, VSS=m.VSS)
    m.encoder = OneHotEncoder(width=4)(bin=count, en=m.VDD, VDD=m.VDD, VSS=m.VSS)
    m.mux = OneHotMux(width=16)(
        inp=m.pdata, out=m.sdata, sel=m.encoder.out, VDD=m.VDD, VSS=m.VSS
    )

    return m


@h.generator
def RxDeSerializer(_: h.HasNoParams) -> h.Module:
    """ RX De-Serializer 
    Includes parallel-clock generation divider """

    m = h.Module()
    m.pdata = h.Output(width=16, desc="Parallel Output Data")
    m.sdata = h.Input(width=1, desc="Serial Input Data")
    m.pclk = h.Output(width=1, desc="*Output*, Divided Parallel Clock")
    m.sclk = h.Input(width=1, desc="Input Serial Clock")

    # Create the four-bit counter state, consisting of the parallel clock as MSB,
    # and three internal-signal LSBs.
    m.count_lsbs = h.Signal(width=3, desc="LSBs of Divider-Counterer")
    count = h.Concat(m.count_lsbs, m.pclk)

    m.counter = Counter(width=4)(clk=m.sclk, out=count)
    m.encoder = OneHotEncoder(width=4)(inp=count)

    # The bank of load-registers, all with data-inputs tied to serial data,
    # "clocked" by the one-hot counter state.
    # Note output `q`s are connected by later instance-generation statements.
    m.load_latches = 8 * Latch()(d=m.sdata, clk=m.encoder.out)
    # The bank of output flops
    m.output_flops = 8 * Flop()(d=m.load_latches.q, q=m.pdata, clk=m.pclk)

    return m


@h.generator
def TxDriver(_: h.HasNoParams) -> h.Module:
    """ Transmit Driver """

    m = h.Module()
    m.VDD, m.VSS = h.Ports(2)

    m.data = h.Input(width=1)  # Data Input
    m.pads = Diff(port=True)  # Output pads
    # m.zcal = h.Input(width=32)  # Impedance Control Input
    # FIXME: internal implementation
    # Create the segmented unit drivers
    # m.segments = 32 * TxDriverSegment(pads=pads, en=m.zcal, data=m.data, clk=m.clk)

    return m


@h.bundle
class TxData:
    """ Transmit Data Bundle """

    pdata = h.Input(width=10, desc="Parallel Data Input")
    pclk = h.Output(desc="Output Parallel-Domain Clock")


@h.bundle
class TxConfig:
    """ Transmit Config Bundle """

    ...  # FIXME: contents!


@h.bundle
class TxIo:
    """ Transmit Lane IO """

    pads = Diff(desc="Differential Transmit Pads", role=Diff.Roles.SOURCE)
    data = TxData(desc="Data IO from Core")
    cfg = TxConfig(desc="Configuration IO")


@h.module
class HsTx:
    """ Transmit Lane """

    # IO
    VDD, VSS = h.Ports(2)
    # io = TxIo(port=True) # FIXME: combined bundle
    ## Pad Interface
    pads = Diff(desc="Differential Transmit Pads", port=True, role=Diff.Roles.SOURCE)
    ## Core Interface
    pdata = h.Input(width=16, desc="Parallel Input Data")
    pclk = h.Output(width=1, desc="*Output*, Divided Parallel Clock")
    ## PLL Interface
    sclk = h.Input(width=1, desc="Input Serial Clock")

    # Internal Implementation
    ## Serializer, with internal 8:1 parallel-clock divider
    serializer = TxSerializer()(pdata=pdata, pclk=pclk, sclk=sclk, VDD=VDD, VSS=VSS)
    ## Output Driver
    driver = TxDriver()(data=serializer.sdata, pads=pads, VDD=VDD, VSS=VSS)


@h.module
class Cdr:
    """ 
    # Clock & Data Recovery 
    Analog / Custom Portion 
    
    While afforded a level of Module hierarchy and called "CDR", 
    this is really just the phase interpolator. 
    Control codes are to be generated by external digital logic, 
    and early/ late signals are similarly derived in the parallel digital domain. 
    """

    # IO Interface
    VDD, VSS = h.Ports(2)
    qck = QuadClock(port=True, role=QuadClock.Roles.SINK, desc="Input quadrature clock")
    dck = h.Output(desc="Recovered Data Clock")
    xck = h.Output(desc="Recovered Edge Clock")  # FIXME!
    # FIXME: make the recovered clock differential
    pi_code = h.Input(width=5, desc="Phase Interpolator Code")

    # Implementation
    pi = PhaseInterp(nbits=5)(ckq=qck, sel=pi_code, out=dck, VDD=VDD, VSS=VSS)


@h.module
class HsRx:
    """ # High-Speed Receiver """

    # IO
    # io = RxIo(port=True) # FIXME: combined bundle
    VDD, VSS = h.Ports(2)
    ## Pad Interface
    pads = Diff(desc="Differential Receive Pads", port=True, role=Diff.Roles.SINK)
    ## Core Interface
    pdata = h.Output(width=16, desc="Parallel Output Data")
    pclk = h.Output(width=1, desc="*Output*, Divided Parallel Clock")
    ## CDR
    qck = QuadClock(port=True, role=QuadClock.Roles.SINK)
    pi_code = h.Input(width=5, desc="Phase Interpolator Code")
    dck, xck = h.Outputs(2)

    # Internal Implementation
    ## Clock Recovery
    cdr = Cdr()(qck=qck, dck=dck, xck=xck, pi_code=pi_code, VDD=VDD, VSS=VSS)

    ## Slicers
    # dslicer = Slicer()(inp=pads, out=d, clk=dck)
    # xslicer = Slicer()(inp=pads, out=x, clk=xck)

    ## De-serializer, with internal parallel-clock divider
    # ddser = RxDeSerializer()(sdata=d, pdata=pdata, pclk=pclk, sclk=dck)
    # xdser = RxDeSerializer()(sdata=x, pdata=pdata, pclk=pclk, sclk=dck)


@h.module
class Other:
    ...  # Empty, for now


@h.bundle
class AnaDigBundle:
    """ 
    # Analog-Digital Signal Bundle
    
    Note all port-directions are from the perspective of `Usb2PhyAna`, the analog portion of the PHY. 
    The digital half is not implemented with `hdl21.Bundle` and hence is never instantiated. 
    """

    tx_pdata = h.Input(width=16, desc="Parallel Input Data")
    tx_pclk = h.Output(width=1, desc="*Output*, Divided Parallel Clock")

    rx_pdata = h.Output(width=16, desc="Parallel Output Data")
    rx_pclk = h.Output(width=1, desc="*Output*, Divided Parallel Clock")
    rx_pi_code = h.Input(width=5, desc="Phase Interpolator Code")

    # FIXME: organize these into sub-bundles


@h.module
class Usb2PhyAna:
    """ 
    # USB 2 PHY, Custom / Analog Portion 
    Top-level module and primary export of this package. 
    """

    # IO Interface
    VDD, VSS = h.Ports(2)
    pads = Diff(desc="Differential Pads", port=True, role=None)
    dig_if = AnaDigBundle(port=True)
    qck = QuadClock(port=True, role=QuadClock.Roles.SINK, desc="Input quadrature clock")

    # Implementation
    ## High-Speed TX
    tx = HsTx(
        pads=pads,
        pdata=dig_if.tx_pdata,
        pclk=dig_if.tx_pclk,
        sclk=qck.ck0,
        VDD=VDD,
        VSS=VSS,
    )
    ## High-Speed RX
    rx = HsRx(
        pads=pads,
        pdata=dig_if.rx_pdata,
        pclk=dig_if.rx_pclk,
        pi_code=dig_if.rx_pi_code,
        qck=qck,
        dck=h.NoConn(),  # FIXME!
        xck=h.NoConn(),  # FIXME!
        VDD=VDD,
        VSS=VSS,
    )
    ## All the other stuff: squelch etc.
    ## Broken out into more Modules as we go.
    other = Other()

