""" 
# RX De-Serializer 
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from ..logiccells import Latch, Flop
from ..encoders import OneHotEncoder
from ..counter import Counter


@h.generator
def RxDeSerializer(_: h.HasNoParams) -> h.Module:
    """RX De-Serializer
    Includes parallel-clock generation divider"""

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
