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


@h.generator
def HsRx(_: h.HasNoParams) -> h.Module:
    """# High-Speed Receiver"""

    @h.module
    class HsRx:

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
        preamp = PreAmp(h.Default)(
            inp=pads, pbias=pbias_preamp_200u, VDD33=SUPPLIES.VDD33, VSS=SUPPLIES.VSS
        )
        ## Clock Recovery
        cdr = Cdr(h.Default)(
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
        slicer = Slicer(h.Default)(
            inp=preamp.out,
            clk=sck,
            out=h.bundlize(p=sdata, n=sdata_n),
            VDD18=SUPPLIES.VDD18,
            VSS=SUPPLIES.VSS,
        )

    return HsRx
