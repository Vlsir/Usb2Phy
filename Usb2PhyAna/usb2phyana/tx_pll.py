import hdl21 as h

# Local Imports
from .supplies import PhySupplies
from .ilo import Ilo


@h.module
class RefClkPulseGen:
    """Reference Clock Pulse Generator"""

    # IO Interface
    ## Supplies
    SUPPLIES = PhySupplies(port=True)
    ## Clock Input
    refck = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="Reference Clock")
    inj = h.Output(desc="Injection Output")
    en = h.Input(desc="Enable")

    # Implementation
    ## FIXME!


@h.generator
def TxPll(_: h.HasNoParams) -> h.Module:
    @h.module
    class TxPll:
        """# Transmit PLL"""

        # IO Interface
        ## Supplies
        SUPPLIES = PhySupplies(port=True)

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
        fctrl = h.Input(width=5, desc="RX Frequency Control Code")

        # Implementation
        inj = h.Signal()
        ## FIXME! add the pulse generation
        pulse_gen = RefClkPulseGen(refck=refck, en=phase_en, SUPPLIES=SUPPLIES)
        ilo = Ilo(h.Default)(
            VDDA33=SUPPLIES.VDD33,
            VDD18=SUPPLIES.VDD18,
            VSS=SUPPLIES.VSS,
            inj=pulse_gen.inj,
            pbias=SUPPLIES.VSS,  # FIXME!!
            fctrl=fctrl,
            sck=txsck.p,  # FIXME: do we want the Diff in here?
        )
        ## Output bypass mux
        # bypass_mux = BypassMux()

    return TxPll
