""" 
USB 2.0 Phy Custom / Analog
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from .supplies import PhySupplies
from .hstx import HsTx
from .hsrx import HsRx
from .tx_pll import TxPll


@h.bundle
class AnaDigBundle:
    """
    # Analog-Digital Signal Bundle
    Interface to the digital portion of the PHY

    Note all port-directions are from the perspective of `Usb2PhyAna`, the analog portion of the PHY.
    The digital half is not implemented with `hdl21.Bundle` and hence is never instantiated.
    """

    hstx_sck = h.Output(width=1, desc="High-Speed TX *Output* Serial TX Clock")
    hstx_sdata = h.Input(width=1, desc="High-Speed TX Data")
    hstx_shunt = h.Input(width=1, desc="High-Speed TX Shunt Drive Current")
    hstx_en = h.Input(width=1, desc="High-Speed TX Output Enable")

    hstx_pll_fctrl = h.Input(width=5, desc="TX Frequency Control Code")
    hstx_pll_en = h.Input(desc="TX PLL Enable")
    hstx_pll_phase_en = h.Input(desc="TX PLL Phase-Path Enable")
    hstx_pll_bypass = h.Input(desc="Bypass TX PLL")

    hsrx_sck = h.Output(width=1, desc="*Output* RX Recovered Clock")
    hsrx_sdata = h.Output(width=1, desc="Serial RX Data")
    hsrx_fctrl = h.Input(width=5, desc="RX Frequency Control Code")
    hsrx_cdr_en = h.Input(desc="RX CDR Enable")

    squelch = h.Output(width=1, desc="Squelch Detector Output")
    fstx_pd_en = h.Input(desc="Full-speed pull-down enable")
    fstx_pu_en = h.Input(desc="Full-speed pull-up enable")
    fsrx_diff = h.Output(desc="Differential Full-Speed RX")
    fsrx_linestate_p, fsrx_linestate_n = h.Outputs(2, desc="Single Ended Line State")

    # FIXME: organize these into sub-bundles


@h.module
class FsTx:
    """USB Full-Speed (12Mb) TX"""

    # IO
    SUPPLIES = PhySupplies(port=True)
    pd_en, pu_en = h.Inputs(2)
    pads = h.Diff(desc="Differential Pads", port=True, role=h.Diff.Roles.SOURCE)

    # Implementation
    # FIXME: the actual implementation!


@h.generator
def Usb2PhyAna(_: h.HasNoParams) -> h.Module:
    @h.module
    class Usb2PhyAna:
        """
        # USB 2 PHY, Custom / Analog Portion
        Top-level module and primary export of this package.
        """

        # IO Interface
        SUPPLIES = PhySupplies(port=True)

        pads = h.Diff(port=True, role=None, desc="Differential Pads")
        dig_if = AnaDigBundle(port=True, desc="Analog-Digital Interface")
        refck = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="Reference Clock")
        bypck = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="TX PLL Bypass Clock")

        # Implementation
        # FIXME: feeds into dig_if
        hstx_sck = h.Diff(desc="TX Serial Clock", port=False, role=None)
        hsrx_sck = h.Diff(desc="RX Serial Clock", port=False, role=None)

        ## Bias Signals
        ## FIXME: add a bias block and generate these!
        pbias, nbias = h.Signals(2)

        ## Tx PLL
        txpll = TxPll(h.Default)(
            en=SUPPLIES.VDD18,  # FIXME!
            phase_en=dig_if.hstx_pll_phase_en,
            bypass=dig_if.hstx_pll_bypass,
            refck=refck,
            bypck=bypck,
            txsck=hstx_sck,
            SUPPLIES=SUPPLIES,
        )

        ## High-Speed TX
        tx = HsTx(h.Default)(
            pads=pads,
            sdata=dig_if.hstx_sdata,
            sck=hstx_sck,
            shunt=SUPPLIES.VSS,  # FIXME!
            en=SUPPLIES.VSS,  # FIXME!
            pbias=pbias,
            nbias=nbias,
            SUPPLIES=SUPPLIES,
        )
        ## High-Speed RX
        rx = HsRx(h.Default)(
            pads=pads,
            sck=dig_if.hsrx_sck,
            sdata=dig_if.hsrx_sdata,
            fctrl=dig_if.hsrx_fctrl,
            cdr_en=dig_if.hsrx_cdr_en,
            pbias_cdr_120u=SUPPLIES.VSS,  # FIXME!
            pbias_preamp_200u=SUPPLIES.VSS,  # FIXME!
            SUPPLIES=SUPPLIES,
        )
        ## All the other stuff: squelch etc.
        ## Broken out into more Modules as we go.
        other = Other()

    return Usb2PhyAna


@h.module
class Other:
    """
    All the other stuff: squelch etc.
    Broken out into more Modules as we go.
    """

    ...  # Empty, for now
