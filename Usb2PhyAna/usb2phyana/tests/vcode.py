""" 
Binary-Valued DC Volage Bus Generator 
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21.primitives import Vdc


@h.paramclass
class Params:
    """`Vcode` Parameters"""

    # Required
    code = h.Param(dtype=int, desc="Binary-Valued Code")
    width = h.Param(dtype=int, desc="Bus Width")
    vhi = h.Param(dtype=h.Prefixed, desc="High Voltage Level")
    # Optional
    vlo = h.Param(dtype=h.Prefixed, desc="Low Voltage Level", default=0 * h.Prefix.UNIT)


@h.generator
def Vcode(params: Params) -> h.Module:
    """Binary-Valued DC Volage Bus Generator"""

    if params.code < 0:
        raise ValueError("Code must be positive")

    # Set up the Module and its IO interface: code output and VSS.
    m = h.Module()
    m.code = h.Output(width=params.width)
    m.VSS = h.Port()

    def vbit(i: int) -> Vdc:
        """Create a `Vdc` call equal to either `params.vhi` or `params.vlo`."""
        val = params.vhi if i else params.vlo
        return Vdc(Vdc.Params(dc=val, ac=0 * h.Prefix.UNIT))

    # Convert the binary integer value to a binary-valued string
    bits = bin(params.code)[2:].zfill(params.width)

    # And create a voltage source for each bit
    for idx in range(params.width):
        bitval = int(bits[-(idx + 1)])
        vinst = vbit(bitval)(p=m.code[idx], n=m.VSS)
        m.add(name=f"vcode{idx}", val=vinst)

    return m
