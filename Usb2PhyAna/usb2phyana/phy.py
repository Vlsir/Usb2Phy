""" 
USB 2.0 Phy Custom / Analog
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
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
class PhySupplies:
    """
    # PHY Supply & Ground Signals
    """

    VDD18, VDD33, VSS = h.Signals(3)


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

    VDD18, VDD33, VSS = h.Ports(3)
    pd_en, pu_en = h.Inputs(2)
    pads = h.Diff(desc="Differential Pads", port=True, role=h.Diff.Roles.SOURCE)

    # FIXME: the actual implementation!


@h.generator
def TxPll(_: h.HasNoParams) -> h.Module:
    @h.module
    class TxPll:
        """# Transmit PLL"""

        # IO Interface
        ## Supplies
        VDD18, VDD33, VSS = h.Ports(3)

        ## Primary Input & Output Clocks
        refck = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="Reference Clock")
        bypck = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="Bypass Clock")
        txsck = h.Diff(
            port=True, role=h.Diff.Roles.SOURCE, desc="Output TX Serial Clock"
        )

        ## Controls
        en = h.Input(desc="PLL Enable")
        phase_en = h.Input(desc="Phase Path Enable")
        bypass = h.Input(desc="PLL Bypass Enable")

        # Implementation
        ## FIXME!
        # ilo = Ilo()()
        # bypass_mux = BypassMux()()

    return TxPll


@h.generator
def Usb2PhyAna(_: h.HasNoParams) -> h.Module:
    @h.module
    class Usb2PhyAna:
        """
        # USB 2 PHY, Custom / Analog Portion
        Top-level module and primary export of this package.
        """

        # IO Interface
        VDD18, VDD33, VSS = h.Ports(3)
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
            en=VDD18,  # FIXME!
            phase_en=dig_if.hstx_pll_phase_en,
            bypass=dig_if.hstx_pll_bypass,
            refck=refck,
            bypck=bypck,
            txsck=hstx_sck,
            VDD18=VDD18,
            VDD33=VDD33,
            VSS=VSS,
        )

        ## High-Speed TX
        tx = HsTx(h.Default)(
            pads=pads,
            sdata=dig_if.hstx_sdata,
            sclk=hstx_sck,
            pbias=pbias,
            nbias=nbias,
            VDD18=VDD18,
            VDD33=VDD33,
            VSS=VSS,
        )
        ## High-Speed RX
        rx = HsRx(h.Default)(
            pads=pads,
            sck=dig_if.hsrx_sck,
            sdata=dig_if.hsrx_sdata,
            fctrl=dig_if.hsrx_fctrl,
            cdr_en=dig_if.hsrx_cdr_en,
            pbias=pbias,
            nbias=nbias,
            VDD18=VDD18,
            VDD33=VDD33,
            VSS=VSS,
        )
        ## All the other stuff: squelch etc.
        ## Broken out into more Modules as we go.
        other = Other()

    return Usb2PhyAna
