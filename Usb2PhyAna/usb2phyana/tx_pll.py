import hdl21 as h

# Local Imports
from .phyroles import PhyRoles
from .supplies import PhySupplies
from .ilo import Ilo


@h.bundle
class TxPllClocks:
    """# TX PLL Clocks"""

    Roles = PhyRoles  # Set the shared PHY Roles

    refck = h.Diff(desc="Reference Clock")
    bypck = h.Diff(desc="Bypass Clock")
    txsck = h.Diff(desc="TX Serial Clock")


@h.bundle
class TxPllCtrl:
    """# TX PLL Control"""

    Roles = PhyRoles  # Set the shared PHY Roles

    en = h.Input(desc="PLL Enable")
    phase_en = h.Input(desc="Phase Path Enable")
    bypass = h.Input(desc="PLL Bypass Enable")
    fctrl = h.Input(width=5, desc="RX Frequency Control Code")


@h.bundle
class TxPllBias:
    """# TX PLL Bias Bundle"""

    pbias = h.Input(desc="ILO P-Side Bias")


@h.generator
def TxPll(_: h.HasNoParams) -> h.Module:
    """# Injection-Locked Transmit PLL"""

    @h.module
    class TxPll:
        # IO Interface
        SUPPLIES = PhySupplies(port=True, role=PhyRoles.PHY, desc="Supplies")
        ctrl = TxPllCtrl(port=True, role=PhyRoles.PHY, desc="PLL Control")
        bias = TxPllBias(port=True, role=PhyRoles.PHY, desc="PLL Bias")
        ## Primary Input & Output Clocks
        refck = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="Reference Clock")
        bypck = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="Bypass Clock")
        txsck = h.Diff(port=True, role=h.Diff.Roles.SOURCE, desc="TX Serial Clock")

        # Implementation
        pulse_gen = RefClkPulseGen(h.Default)(
            refck=refck, en=ctrl.phase_en, SUPPLIES=SUPPLIES
        )
        ilo = Ilo(h.Default)(
            inj=pulse_gen.inj,
            pbias=bias.pbias,
            fctrl=ctrl.fctrl,
            sck=txsck.p,  # FIXME: do we want the Diff in here?
            SUPPLIES=SUPPLIES,
        )
        ## Output bypass mux
        bypass_mux = BypassMux(h.Default)(
            refck=refck, bypck=bypck, txsck=txsck, bypass=ctrl.bypass, SUPPLIES=SUPPLIES
        )

    return TxPll


@h.generator
def RefClkPulseGen(_: h.HasNoParams) -> h.Module:
    """Reference Clock Pulse Generator"""

    @h.module
    class RefClkPulseGen:

        # IO Interface
        ## Supplies
        SUPPLIES = PhySupplies(port=True)
        ## Clock Input
        refck = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="Reference Clock")
        inj = h.Output(desc="Injection Output")
        en = h.Input(desc="Enable")

        # Implementation
        ## FIXME!

    return RefClkPulseGen


@h.generator
def BypassMux(_: h.HasNoParams) -> h.Module:
    """Bypass Clock Mux Generator"""

    @h.module
    class BypassMux:
        # IO Interface
        ## Supplies
        SUPPLIES = PhySupplies(port=True)

        ## Primary Input & Output Clocks
        refck = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="Reference Clock")
        bypck = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="Bypass Clock")
        txsck = h.Diff(port=True, role=h.Diff.Roles.SOURCE, desc="TX Serial Clock")

        ## Controls
        bypass = h.Input(desc="PLL Bypass Enable")

        # Implementation
        ## FIXME!

    return BypassMux
