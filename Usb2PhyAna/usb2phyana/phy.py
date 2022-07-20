""" 
USB 2.0 Phy Custom / Analog
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from .diff import Diff
from .quadclock import QuadClock
from .hstx import HsTx
from .hsrx import HsRx


@h.module
class Other:
    """
    All the other stuff: squelch etc.
    Broken out into more Modules as we go.
    """

    ...  # Empty, for now


@h.bundle
class AnaDigBundle:
    """
    # Analog-Digital Signal Bundle
    Interface to the digital portion of the PHY

    Note all port-directions are from the perspective of `Usb2PhyAna`, the analog portion of the PHY.
    The digital half is not implemented with `hdl21.Bundle` and hence is never instantiated.
    """

    tx_sclk = h.Output(width=1, desc="*Output* Serial TX Clock")
    tx_sdata = h.Input(width=1, desc="Serial TX Data")

    fstx_pd_en = h.Input(desc="Full-speed pull-down enable")
    fstx_pu_en = h.Input(desc="Full-speed pull-up enable")

    rx_sclk = h.Output(width=1, desc="*Output* RX Recovered Clock")
    rx_sdata = h.Output(width=1, desc="Serial RX Data")
    rx_edge = h.Output(width=1, desc="RX Edge Samples")
    rx_pi_code = h.Input(width=5, desc="RX Phase Interpolator Code")

    squelch = h.Output(width=1, desc="Squelch Detector Output")

    linestate_p, linestate_n = h.Outputs(2)

    # FIXME: organize these into sub-bundles


@h.module
class FsTx:
    """USB Full-Speed (12Mb) TX"""

    VDD18, VDD33, VSS = h.Ports(3)
    pd_en, pu_en = h.Inputs(2)
    pads = Diff(desc="Differential Pads", port=True, role=Diff.Roles.SOURCE)

    # FIXME: the actual implementation!


@h.module
class TxPll:
    """# Transmit PLL
    Or, for now, a surrogate therefore, dividing a *higher* frequencey "refclk"."""

    VDD18, VDD33, VSS = h.Ports(3)
    en = h.Input(desc="Enable")
    refck = Diff(port=True, role=Diff.Roles.SINK, desc="Reference Clock")
    qck = QuadClock(
        port=True, role=QuadClock.Roles.SOURCE, desc="Output quadrature clock"
    )

    # FIXME: the actual implementation!


@h.module
class Usb2PhyAna:
    """
    # USB 2 PHY, Custom / Analog Portion
    Top-level module and primary export of this package.
    """

    # IO Interface
    VDD18, VDD33, VSS = h.Ports(3)
    pads = Diff(desc="Differential Pads", port=True, role=None)
    dig_if = AnaDigBundle(port=True)
    refck = Diff(port=True, role=Diff.Roles.SINK, desc="Reference Clock")

    # Implementation
    rck = Diff(
        desc="RX Recovered Clock", port=False, role=None
    )  # FIXME: feeds into dig_if.rx_sclk
    qck = QuadClock(desc="Quadrature clock")

    ## Tx PLL / Quadrature Clock Generation
    txpll = TxPll(
        en=VDD18,  # FIXME!
        refck=refck,
        qck=qck,
        VDD18=VDD18,
        VDD33=VDD33,
        VSS=VSS,
    )

    ## High-Speed TX
    tx = HsTx(
        pads=pads,
        sdata=dig_if.tx_sdata,
        sclk=h.AnonymousBundle(p=qck.ck0, n=qck.ck180),
        VDD18=VDD18,
        VDD33=VDD33,
        VSS=VSS,
    )
    ## High-Speed RX
    rx = HsRx(
        pads=pads,
        sclk=dig_if.rx_sclk,
        sdata=dig_if.rx_sdata,
        edge=dig_if.rx_edge,
        pi_code=dig_if.rx_pi_code,
        VDD18=VDD18,
        VDD33=VDD33,
        VSS=VSS,
    )
    ## All the other stuff: squelch etc.
    ## Broken out into more Modules as we go.
    other = Other()
