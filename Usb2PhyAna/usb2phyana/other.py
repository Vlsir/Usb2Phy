""" 
# USB 2.0 Phy 
## Other / Misc Near-Top Level Blocks
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from .phyroles import PhyRoles
from .supplies import PhySupplies
from .hstx import HsTxBias
from .hsrx import HsRxBias
from .tx_pll import TxPllBias


@h.bundle
class PhyBias:
    """# Phy-Level Bias Input(s)"""

    Roles = PhyRoles  # Set the shared PHY Roles
    ibias = h.Signal()  # FIXME: detail this


@h.module
class BiasDist:
    """Bias Distribution"""

    # IO
    SUPPLIES = PhySupplies(port=True, role=PhyRoles.PHY, desc="Supplies")
    phy = PhyBias(port=True, desc="Phy Bias Input(s)")
    txpll = TxPllBias(port=True, desc="Tx Pll Bias")
    hsrx = HsRxBias(port=True, desc="Hs Rx Bias")
    hstx = HsTxBias(port=True, desc="Hs Tx Bias")

    # Implementation
    # FIXME: the actual implementation!


@h.module
class FsTx:
    """USB Full-Speed (12Mb) TX"""

    # IO
    SUPPLIES = PhySupplies(port=True, role=PhyRoles.PHY, desc="Supplies")
    pd_en, pu_en = h.Inputs(2)
    pads = h.Diff(desc="Differential Pads", port=True, role=h.Diff.Roles.SOURCE)

    # Implementation
    # FIXME: the actual implementation!
