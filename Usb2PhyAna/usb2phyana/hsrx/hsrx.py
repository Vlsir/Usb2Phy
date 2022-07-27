"""
# High-Speed RX 
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from .preamp import PreAmp
from .slicer import Slicer
from ..ilo import Ilo


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
        VDD18, VDD33, VSS = h.Ports(3)

        ## Primary IO
        data = h.Diff(port=True, role=h.Diff.Roles.SINK, desc="RX Data")
        sck = h.Output(desc="RX Serial Clock")
        fctrl = h.Input(width=5, desc="RX Frequency Control Code")
        cdr_en = h.Input()
        pbias = h.Input()

        # Implementation
        ## FIXME!
        inj = h.Signal()
        # pulse_gen = DataPulseGen()(data=data)
        ilo = Ilo(Ilo.Params())(  # FIXME!
            VDDA33=VDD33,
            VDD18=VDD18,
            VSS=VSS,
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
        # io = RxIo(port=True) # FIXME: combined bundle

        ## Supplies
        VDD18, VDD33, VSS = h.Ports(3)
        ## Pad Interface
        pads = h.Diff(
            desc="Differential Receive Pads", port=True, role=h.Diff.Roles.SINK
        )
        ## Bias Inputs
        pbias_cdr_120u, pbias_preamp_200u = h.Inputs(2)

        ## Digital Interface
        sck = h.Output(width=1, desc="*Output* RX Recovered Clock")
        sdata = h.Output(width=1, desc="Serial RX Data")
        fctrl = h.Input(width=5, desc="RX Frequency Control Code")
        cdr_en = h.Input(desc="RX CDR Enable")

        # Internal Implementation

        ## Pre-Amp
        preamp = PreAmp(inp=pads, pbias=pbias_preamp_200u, VDD33=VDD33, VSS=VSS)

        ## Clock Recovery
        cdr = Cdr()(
            sck=sck,
            fctrl=fctrl,
            cdr_en=cdr_en,
            data=preamp.out,
            pbias=pbias_cdr_120u,
            VDD33=VDD33,
            VDD18=VDD18,
            VSS=VSS,
        )

        ## Slicer
        sdata_n = h.Signal()
        slicer = Slicer(
            inp=preamp.out,
            clk=sck,
            out=h.AnonymousBundle(p=sdata, n=sdata_n),  # FIXME: enable `NoConn` here
            VDD18=VDD18,
            VSS=VSS,
        )

    return HsRx
