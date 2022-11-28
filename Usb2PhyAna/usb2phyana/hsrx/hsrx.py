"""
# High-Speed RX 
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from .preamp import PreAmp
from .slicer import Slicer
from ..ilo import Ilo
from ..supplies import PhySupplies


@h.generator
def Cdr(_: h.HasNoParams) -> h.Module:
    @h.module
    class Cdr:
        """
        # Clock & Data Recovery
        Analog / Custom Portion
        """

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
            VDDA33=SUPPLIES.VDD33,
            VDD18=SUPPLIES.VDD18,
            VSS=SUPPLIES.VSS,
            inj=inj,
            pbias=pbias,
            fctrl=fctrl,
            sck=sck,
        )

    return Cdr


@h.generator
def HsRx(_: h.HasNoParams) -> h.Module:
    @h.module
    class HsRx:
        """# High-Speed Receiver"""

        # IO
        ## Supplies
        SUPPLIES = PhySupplies(port=True)
        ## Pad Interface
        pads = h.Diff(desc="RX Pads", port=True, role=h.Diff.Roles.SINK)
        ## Bias Inputs
        pbias_cdr_120u, pbias_preamp_200u = h.Inputs(2)

        ## Digital Interface
        sck = h.Output(width=1, desc="*Output* RX Recovered Clock")
        sdata = h.Output(width=1, desc="Serial RX Data")
        fctrl = h.Input(width=5, desc="RX Frequency Control Code")
        cdr_en = h.Input(desc="RX CDR Enable")

        # Internal Implementation
        ## Pre-Amp
        preamp = PreAmp(
            inp=pads, pbias=pbias_preamp_200u, VDD33=SUPPLIES.VDD33, VSS=SUPPLIES.VSS
        )
        ## Clock Recovery
        cdr = Cdr()(
            sck=sck,
            fctrl=fctrl,
            cdr_en=cdr_en,
            data=preamp.out,
            pbias=pbias_cdr_120u,
            SUPPLIES=SUPPLIES,
        )
        ## Slicer
        # FIXME: eventually `sdata_n` here will be able to be a `NoConn`
        sdata_n = h.Signal()
        slicer = Slicer(
            inp=preamp.out,
            clk=sck,
            out=h.AnonymousBundle(p=sdata, n=sdata_n),
            VDD18=SUPPLIES.VDD18,
            VSS=SUPPLIES.VSS,
        )

    return HsRx
