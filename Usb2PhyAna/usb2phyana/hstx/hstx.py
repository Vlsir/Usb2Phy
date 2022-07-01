""" 
# High-Speed TX
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from ..diff import Diff


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
    """ 
    # High-Speed TX
    """

    # IO
    VDD18, VDD33, VSS = h.Ports(3)
    # io = TxIo(port=True) # FIXME: combined bundle
    ## Pad Interface
    pads = Diff(desc="Differential Transmit Pads", port=True, role=Diff.Roles.SOURCE)
    ## Core Interface
    sdata = h.Input(width=1, desc="Serial TX Data")
    ## PLL Interface
    sclk = Diff(desc="Serial Clock", port=True, role=Diff.Roles.SINK) 

    # Internal Implementation
    # ## Output Driver
    # driver = TxDriver()(data=serializer.sdata, pads=pads, VDD=VDD, VSS=VSS)
