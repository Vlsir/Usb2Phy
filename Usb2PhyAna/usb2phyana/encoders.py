"""
# Encoders
Conversion Modules between binary, one-hot, thermometer, and the like. 
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from .width import Width 
from .logiccells import Inv, And2, And3, Or2


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
