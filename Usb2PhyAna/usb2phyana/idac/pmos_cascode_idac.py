"""
# Pmos Cascode Current Dac
"""

# Hdl & PDK Imports
import hdl21 as h
import s130
from s130 import MosParams

from ..logiccells import Inv


Pmos = s130.modules.nmos
PmosLvt = s130.modules.nmos_lvt
Pmos = s130.modules.pmos

# Define a few reused device-parameter combos
Pswitch = Pmos(MosParams(m=4))
# Unit PMOS - sized for 1µA
Pbias = Pmos(w=1, l=1)


@h.module
class PmosIdacUnit:
    """Dac Unit Current"""

    # IO Interface
    VDDA33, VSS = h.Ports(2)
    ## Primary I/O
    en, enb = h.Inputs(2, desc="Unit Current Enable")
    out = h.Output(desc="Dac Output")
    ## Gate Bias
    pbias, cbias = h.Ports(2, desc="Gate Biases for Source & Cascode")
    cascode_source = h.Port(desc="Cascode Source - only for bias unit!")

    # Bias Pmos
    psrc = Pbias(g=pbias, d=cascode_source, s=VDDA33, b=VDDA33)
    # Cascode Pmos
    switch_source = h.Signal()
    pcasc = Pbias(g=cbias, d=switch_source, s=cascode_source, b=VDDA33)
    # Differential Switch Pmoses
    sw_out = Pswitch(g=enb, d=out, s=switch_source, b=VDDA33)
    sw_vss = Pswitch(g=en, d=VSS, s=switch_source, b=VDDA33)


@h.generator
def PmosIdac(_: h.HasNoParams) -> h.Module:
    """# Pmos Current Dac"""

    @h.module
    class PmosIdac:
        # IO Interface
        VDDA33, VDD18, VSS = h.Ports(3)
        ## Primary I/O
        code = h.Input(width=5, desc="Dac Code")
        out = h.Output(desc="Dac Output")
        ## Bias input
        ibias = h.Input(desc="Current Bias Input")

        # Internal Implementation
        codeb = h.Signal(width=5)
        code_invs = 5 * Inv()(i=code, z=codeb, VDD=VDD18, VSS=VSS)

        ## Diode Connected Bias Unit
        pbias = h.Signal()
        udiode = 128 * PmosIdacUnit(
            out=ibias,
            cbias=ibias,
            pbias=pbias,
            cascode_source=pbias,
            en=VDD18,
            enb=VSS,
            VDDA33=VDDA33,
            VSS=VSS,
        )
        ## Always-On Units
        uon = 128 * PmosIdacUnit(
            out=out,
            cbias=ibias,
            pbias=pbias,
            cascode_source=h.NoConn(),
            en=VDD18,
            enb=VSS,
            VDDA33=VDDA33,
            VSS=VSS,
        )

    ## Primary Dac Units
    ## Give `PmosIdac` a shorter identifier for adding these
    P = PmosIdac

    ## Sizes per bit: 4, 8, 16, etc
    size = lambda idx: 4 * (2**idx)

    for idx in range(5):
        inst = size(idx) * PmosIdacUnit(
            out=P.out,
            cbias=P.ibias,
            pbias=P.pbias,
            cascode_source=h.NoConn(),
            en=P.code[idx],
            enb=P.codeb[idx],
            VDDA33=P.VDDA33,
            VSS=P.VSS,
        )
        P.add(inst, name=f"u{idx}")

    return PmosIdac
