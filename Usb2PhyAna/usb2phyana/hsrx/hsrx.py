"""
# High-Speed RX 
"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from .preamp import PreAmp
from .slicer import Slicer


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
        rck = h.Diff(
            port=True, role=h.Diff.Roles.SOURCE, desc="Recovered Differential Clock"
        )
        fctrl = h.Input(width=5, desc="RX Frequency Control Code")
        cdr_en = h.Input()

        # Implementation
        ## FIXME!
        # pulse_gen = DataPulseGen()(data=data)
        # ilo = Ilo()()

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
        pbias, nbias = h.Inputs(2)

        ## Digital Interface
        sck = h.Output(width=1, desc="*Output* RX Recovered Clock")
        sdata = h.Output(width=1, desc="Serial RX Data")
        fctrl = h.Input(width=5, desc="RX Frequency Control Code")
        cdr_en = h.Input(desc="RX CDR Enable")

        # Internal Implementation
        rck = h.Diff(port=False, desc="Recovered Differential Clock")
        ## FIXME: diff to se driver for `rck` to create output `sclk`
        ## Pre-Amp
        preamp = PreAmp(inp=pads, pbias=pbias, VDD33=VDD33, VSS=VSS)
        ## Clock Recovery
        cdr = Cdr()(
            rck=rck,
            fctrl=fctrl,
            cdr_en=cdr_en,
            data=preamp.out,
            VDD33=VDD33,
            VDD18=VDD18,
            VSS=VSS,
        )
        ## Slicer
        sdata_n = h.Signal()
        slicer = Slicer(
            inp=preamp.out,
            clk=rck.p,
            out=h.AnonymousBundle(p=sdata, n=sdata_n),  # FIXME: enable `NoConn` here
            VDD18=VDD18,
            VSS=VSS,
        )

    return HsRx
