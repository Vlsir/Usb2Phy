"""
# One-Hot Rotator
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from ..width import Width
from ..logiccells import Inv, And2, FlopResetLow, FlopResetHigh


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
