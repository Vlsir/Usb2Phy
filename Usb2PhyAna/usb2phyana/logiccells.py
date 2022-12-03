"""
# Phy General-Purpose Logic Cells

A combination of "headers" for pre-simulation wrappers, 
and PDK-provided logic cells. 
"""

# Hdl & PDK Imports
import hdl21 as h

# Logic cells from the technology library
from s130.scs130lp import *

"""
Generic "Headers" for Theoretical, Descriptive External Modules 
These of course do not simulate, but serve as stand-ins for compilation targets, 
or just descriptive pre-simulation models. 
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
