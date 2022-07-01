""" 
# TX Serializer
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from ..diff import Diff
from ..width import Width
from ..encoders import OneHotEncoder
from ..counter import Counter
from ..triinv import TriInv


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

