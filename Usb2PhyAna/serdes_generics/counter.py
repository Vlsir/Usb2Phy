# Std-Lib Imports
from typing import Dict
from enum import Enum, auto

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from .width import Width
from .logiccells import Inv, Flop


@h.generator
def Counter(p: Width) -> h.Module:
    """# Binary Counter Generator"""

    m = h.Module()
    m.VDD, m.VSS = h.Ports(2)
    m.clk = h.Input(desc="Primary input. Increments state on each rising edge.")
    m.out = h.Output(width=p.width, desc="Counterer Output State")

    # Divide-by-two stages
    m.invs = p.width * Inv()(i=m.out, VDD=m.VDD, VSS=m.VSS)
    m.flops = p.width * Flop()(d=m.invs.z, q=m.out, clk=m.clk, VDD=m.VDD, VSS=m.VSS)
    return m
