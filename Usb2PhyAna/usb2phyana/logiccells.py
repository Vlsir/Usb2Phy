# Std-Lib Imports
from typing import Dict
from enum import Enum, auto

# Hdl & PDK Imports
import hdl21 as h


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
