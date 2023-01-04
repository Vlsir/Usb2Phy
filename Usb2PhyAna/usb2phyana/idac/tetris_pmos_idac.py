"""
# Tetris-Based Pmos Current Dac
"""

# Hdl & PDK Imports
import hdl21 as h

from ..tetris.mos import Pmos
from ..logiccells import Inv

# Unit PMOS - sized for 64µA
Pbias = Pmos(npar=48, nser=4)
Pswitch = Pmos(npar=16, nser=1)


@h.module
class PmosIdacUnit:
    """Dac Unit Current"""

    # IO Interface
    VDD18, VSS = h.Ports(2)
    ## Primary I/O
    enb = h.Input(desc="Unit Current Enable, Active Low")
    out = h.Output(desc="Dac Current-Mode Output")
    ## Gate Bias
    pbias = h.Port(desc="Gate Bias")

    # Bias Pmos
    psrc = Pbias(g=pbias, s=VDD18, VDD=VDD18, VSS=VSS)
    # Switch Pmos
    psw = Pswitch(g=enb, d=out, s=psrc.d, VDD=VDD18, VSS=VSS)


@h.generator
def PmosIdac(_: h.HasNoParams) -> h.Module:
    """# Pmos Current Dac"""

    @h.module
    class PmosIdac:
        # IO Interface
        VDD18, VSS = h.Ports(2)
        ## Primary I/O
        code = h.Input(width=5, desc="Dac Code")
        out = h.Output(desc="Dac Output")
        ## Bias input
        ibias = h.Input(desc="Current Bias Input")

        # Internal Implementation
        codeb = h.Signal(width=5)
        code_invs = 5 * Inv()(i=code, z=codeb, VDD=VDD18, VSS=VSS)

        ## Diode Connected Bias Unit
        ## Total 6 * 64µA = 384µA
        udiode = 6 * PmosIdacUnit(
            out=ibias,
            pbias=ibias,
            enb=VSS,
            VDD18=VDD18,
            VSS=VSS,
        )
        ## Always-On Units
        ## Total 16 * 64µA = 1.024mA
        uon = 16 * PmosIdacUnit(
            out=out,
            pbias=ibias,
            enb=VSS,
            VDD18=VDD18,
            VSS=VSS,
        )

    ## Primary Dac Units
    ## Give `PmosIdac` a shorter identifier for adding these
    P = PmosIdac

    ## Total 31 * 64µA = 1984µA
    size = lambda idx: (2**idx)
    for idx in range(5):
        inst = size(idx) * PmosIdacUnit(
            out=P.out,
            pbias=P.ibias,
            enb=P.codeb[idx],
            VDD18=P.VDD18,
            VSS=P.VSS,
        )
        P.add(inst, name=f"u{idx}")

    return PmosIdac
