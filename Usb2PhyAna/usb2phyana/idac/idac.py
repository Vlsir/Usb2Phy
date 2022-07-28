"""
# Current DAC(s)
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21.primitives import Res, Cap, Vdc
from hdl21.prefix import m
import s130
from s130 import MosParams


Nmos = s130.modules.nmos
NmosLvt = s130.modules.nmos_lvt
Pmos = s130.modules.pmos

# Define a few reused device-parameter combos
Pswitch = Pmos(MosParams(m=10))
Pbias = Pmos(MosParams(w=1, l=1, m=100))


@h.generator
def NmosIdac(_: h.HasNoParams) -> h.Module:
    """# Nmos Current Dac"""

    Nswitch = NmosLvt(MosParams(m=4))
    Nbias = NmosLvt(MosParams(w=1, l=20, m=1))

    @h.module
    class NmosIdacUnit:
        """Dac Unit Current"""

        # IO Interface
        VSS = h.Port()
        ## Primary I/O
        en = h.Input(desc="Unit Current Enable")
        out = h.Output(desc="Dac Output")
        ## Gate Bias
        bias = h.Input(desc="Current Bias Input")

        # Switch Nmos
        nsw = Nswitch(g=en, d=out, b=VSS)
        # Bias Nmos
        nb = Nbias(g=bias, d=nsw.s, s=VSS, b=VSS)

    @h.module
    class NmosIdac:
        # IO Interface
        VDD, VSS = h.Ports(2)
        ## Primary I/O
        code = h.Input(width=5, desc="Dac Code")
        out = h.Output(desc="Dac Output")
        ## Bias input
        ibias = h.Input(desc="Current Bias Input")

        # Internal Implementation
        ## Diode Transistor, with Drain Switch
        udiode = 64 * NmosIdacUnit(bias=ibias, out=ibias, en=VDD, VSS=VSS)
        ## Always-On Current Transistor
        uon = 64 * NmosIdacUnit(bias=ibias, out=out, en=VDD, VSS=VSS)
        ## Primary Dac Units
        u0 = 2 * NmosIdacUnit(bias=ibias, out=out, en=code[0], VSS=VSS)
        u1 = 4 * NmosIdacUnit(bias=ibias, out=out, en=code[1], VSS=VSS)
        u2 = 8 * NmosIdacUnit(bias=ibias, out=out, en=code[2], VSS=VSS)
        u3 = 16 * NmosIdacUnit(bias=ibias, out=out, en=code[3], VSS=VSS)
        u4 = 32 * NmosIdacUnit(bias=ibias, out=out, en=code[4], VSS=VSS)

    return NmosIdac
