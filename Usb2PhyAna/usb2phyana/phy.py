""" 
# USB 2.0 Phy 
## Custom / Analog Top-Level
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from .phyroles import PhyRoles
from .supplies import PhySupplies
from .hstx import HsTx, HsTxDig
from .hsrx import HsRx, HsRxDig
from .tx_pll import TxPll, TxPllCtrl
from .other import PhyBias, BiasDist


@h.bundle
class AnaDigBundle:
    """
    # Analog-Digital Signal Bundle
    Interface to the digital portion of the PHY

    Note all port-directions are from the perspective of `Usb2PhyAna`, the analog portion of the PHY.
    The digital half is not implemented with `hdl21.Bundle` and hence is never instantiated.
    """

    Roles = PhyRoles  # Set the shared PHY Roles

    # Sub-Block Interfaces
    hstx = HsTxDig(desc="High-Speed TX Digital IO")
    hsrx = HsRxDig(desc="High-Speed RX Digital IO Bundle")
    txpll = TxPllCtrl(desc="High-Speed TX PLL Control")

    # Other/ Misc Signals
    squelch = h.Output(width=1, desc="Squelch Detector Output")
    fstx_pd_en = h.Input(desc="Full-speed pull-down enable")
    fstx_pu_en = h.Input(desc="Full-speed pull-up enable")
    fsrx_diff = h.Output(desc="Differential Full-Speed RX")
    fsrx_linestate_p, fsrx_linestate_n = h.Outputs(2, desc="Single Ended Line State")


@h.generator
def Usb2PhyAna(_: h.HasNoParams) -> h.Module:
    """
    # USB 2 PHY, Custom / Analog Portion
    Top-level module and primary export of this package.
    """

    @h.module
    class Usb2PhyAna:
        # IO Interface
        SUPPLIES = PhySupplies(port=True, role=PhyRoles.PHY, desc="Supplies")
        pads = h.Diff(port=True, role=None, desc="Differential Pads")
        dig_if = AnaDigBundle(port=True, desc="Analog-Digital Interface")
        refck = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="Reference Clock")
        bypck = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="TX PLL Bypass Clock")
        bias = PhyBias(port=True, role=PhyRoles.PHY, desc="Phy Bias Input(s)")

        # Implementation
        ## Bias Distribution
        biasdist = BiasDist(phy=bias, SUPPLIES=SUPPLIES)
        ## Tx PLL
        txpll = TxPll(h.Default)(
            refck=refck,  # Clocks
            bypck=bypck,
            ctrl=dig_if.txpll,  # Control Interface
            bias=biasdist.txpll,  # Bias
            SUPPLIES=SUPPLIES,  # Supplies
        )
        ## High-Speed TX
        tx = HsTx(h.Default)(
            pads=pads,  # Pads
            pllsck=txpll.txsck,  # TxPll Output Clock
            dig=dig_if.hstx,  # Digital Interface
            bias=biasdist.hstx,  # Bias
            SUPPLIES=SUPPLIES,  # Supplies
        )
        ## High-Speed RX
        rx = HsRx(h.Default)(
            pads=pads,  # Pads
            dig=dig_if.hsrx,  # Digital Interface
            bias=biasdist.hsrx,  # Bias
            SUPPLIES=SUPPLIES,  # Supplies
        )

    return Usb2PhyAna
