"""
# Pulse Generator
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from .phyroles import PhyRoles
from .supplies import PhySupplies
from .logiccells import Nor2, Inv, Xor2


@h.generator
def PulseGen(_: h.HasNoParams) -> h.Module:
    """# Injection Pulse Generator"""

    @h.module
    class PulseGen:
        # IO Interface
        SUPPLIES = PhySupplies(port=True, role=PhyRoles.PHY, desc="Supplies")
        inp = h.Input(desc="Primary Input")
        en = h.Input(desc="Enable")
        pulse = h.Output(desc="Output Pulse")

        # Implementation
        ## Internal Signals
        en_n, inp_n, inp_dly = h.Signals(3)

        # Invert Enable
        ien = Inv()(i=en, z=en_n, VDD=SUPPLIES.VDD18, VSS=SUPPLIES.VSS)
        # Enable Gating
        nr_en = Nor2()(a=inp, b=en_n, z=inp_n, VDD=SUPPLIES.VDD18, VSS=SUPPLIES.VSS)
        # Delay Invs
        idly0 = Inv()(i=inp_n, z=inp_dly, VDD=SUPPLIES.VDD18, VSS=SUPPLIES.VSS)

        # Output Pulse Generation
        nr_pulse = Xor2()(
            a=inp_dly, b=inp, z=pulse, VDD=SUPPLIES.VDD18, VSS=SUPPLIES.VSS
        )

    return PulseGen
