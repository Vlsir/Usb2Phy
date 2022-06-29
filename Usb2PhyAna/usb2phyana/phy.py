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
    
    Note all port-directions are from the perspective of `Usb2PhyAna`, the analog portion of the PHY. 
    The digital half is not implemented with `hdl21.Bundle` and hence is never instantiated. 
    """

    tx_pdata = h.Input(width=16, desc="Parallel Input Data")
    tx_pclk = h.Output(width=1, desc="*Output*, Divided Parallel Clock")

    rx_pdata = h.Output(width=16, desc="Parallel Output Data")
    rx_pclk = h.Output(width=1, desc="*Output*, Divided Parallel Clock")
    rx_pi_code = h.Input(width=5, desc="Phase Interpolator Code")

    # FIXME: organize these into sub-bundles


@h.module
class Usb2PhyAna:
    """ 
    # USB 2 PHY, Custom / Analog Portion 
    Top-level module and primary export of this package. 
    """

    # IO Interface
    VDD, VSS = h.Ports(2)
    pads = Diff(desc="Differential Pads", port=True, role=None)
    dig_if = AnaDigBundle(port=True)
    qck = QuadClock(port=True, role=QuadClock.Roles.SINK, desc="Input quadrature clock")
    rck = Diff(desc="RX Recovered Clock", port=False, role=None)

    # Implementation
    ## High-Speed TX
    tx = HsTx(
        pads=pads,
        pdata=dig_if.tx_pdata,
        pclk=dig_if.tx_pclk,
        sclk=qck.ck0,
        VDD=VDD,
        VSS=VSS,
    )
    ## High-Speed RX
    rx = HsRx(
        pads=pads,
        pdata=dig_if.rx_pdata,
        pclk=dig_if.rx_pclk,
        pi_code=dig_if.rx_pi_code,
        qck=qck,
        rck=rck,
        VDD=VDD,
        VSS=VSS,
    )
    ## All the other stuff: squelch etc.
    ## Broken out into more Modules as we go.
    other = Other()
