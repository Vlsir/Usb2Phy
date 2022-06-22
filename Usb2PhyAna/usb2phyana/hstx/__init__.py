""" 
# High-Speed TX
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
