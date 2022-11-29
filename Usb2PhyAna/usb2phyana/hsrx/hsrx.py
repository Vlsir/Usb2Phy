"""
# High-Speed RX 
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from .preamp import PreAmp
from .slicer import Slicer
from ..ilo import Ilo
from ..phyroles import PhyRoles
from ..supplies import PhySupplies


@h.bundle
class HsRxBias:
    """# High-Speed RX Bias Bundle"""

    Roles = PhyRoles  # Set the shared PHY Roles
    pbias_cdr_120u, pbias_preamp_200u = h.Inputs(2)


@h.bundle
class HsRxDig:
    """# High-Speed RX Digital IO Bundle"""

    Roles = PhyRoles  # Set the shared PHY Roles
    sck = h.Output(width=1, desc="*Output* RX Recovered Clock")
    sdata = h.Output(width=1, desc="Serial RX Data")
    fctrl = h.Input(width=5, desc="RX Frequency Control Code")
    cdr_en = h.Input(desc="RX CDR Enable")


@h.generator
def HsRx(_: h.HasNoParams) -> h.Module:
    """# High-Speed Receiver"""

    @h.module
    class HsRx:
        # IO
        SUPPLIES = PhySupplies(port=True, role=PhyRoles.PHY, desc="Supplies")
        dig = HsRxDig(port=True, role=PhyRoles.PHY, desc="Digital IO")
        pads = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="RX Pads")
        bias = HsRxBias(port=True, role=PhyRoles.PHY, desc="Bias Inputs")

        # Implementation
        ## Pre-Amp
        preamp = PreAmp(h.Default)(
            inp=pads,
            pbias=bias.pbias_preamp_200u,
            VDD33=SUPPLIES.VDD33,
            VSS=SUPPLIES.VSS,
        )
        ## Clock Recovery
        cdr = Cdr(h.Default)(
            sck=dig.sck,
            fctrl=dig.fctrl,
            cdr_en=dig.cdr_en,
            data=preamp.out,
            pbias=bias.pbias_cdr_120u,
            SUPPLIES=SUPPLIES,
        )
        ## Slicer
        sdata_n = h.Signal()
        slicer = Slicer(h.Default)(
            inp=preamp.out,
            clk=dig.sck,
            out=h.bundlize(p=dig.sdata, n=sdata_n),
            VDD18=SUPPLIES.VDD18,
            VSS=SUPPLIES.VSS,
        )

    return HsRx


@h.generator
def Cdr(_: h.HasNoParams) -> h.Module:
    """
    # Clock & Data Recovery
    Analog / Custom Portion
    """

    @h.module
    class Cdr:

        # IO Interface
        ## Supplies
        SUPPLIES = PhySupplies(port=True)

        ## Primary IO
        data = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="RX Data")
        sck = h.Output(desc="RX Serial Clock")
        fctrl = h.Input(width=5, desc="RX Frequency Control Code")
        cdr_en = h.Input()
        pbias = h.Input()

        # Implementation
        inj = h.Signal()
        ## FIXME! add the pulse generation
        # pulse_gen = DataPulseGen()(data=data)
        ilo = Ilo(h.Default)(
            inj=inj,
            pbias=pbias,
            fctrl=fctrl,
            sck=sck,
            SUPPLIES=SUPPLIES,
        )

    return Cdr
