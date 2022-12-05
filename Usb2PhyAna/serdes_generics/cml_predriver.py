""" 
# CML Pre-Driver
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21 import Diff
from hdl21.primitives import R
import s130
from s130 import IoMosParams

Pmos = s130.modules.nmos
PmosLvt = s130.modules.nmos_lvt
Pmos = s130.modules.pmos
PmosV5 = s130.modules.pmos_v5
NmosV5 = s130.modules.nmos_v5
Nmos = s130.modules.nmos
NmosLvt = s130.modules.nmos_lvt


@h.bundle
class Triple:
    a, b, c = h.Signals(3)


@h.generator
def CmlPreDriver(_: h.HasNoParams) -> h.Module:
    """# CML Pre-Driver"""

    # Define a few reused device-parameter combos
    MIRROR_RATIO = 40
    PswitchMini = PmosV5(IoMosParams(m=4))
    Pswitch = PmosV5(IoMosParams(m=4 * MIRROR_RATIO))
    Pbias = PmosV5(IoMosParams(l=1, m=10))

    m = h.Module()
    m.VDD18, m.VDD33, m.VSS = h.Ports(3)

    # Primary I/O
    m.inp = Triple(port=True)
    m.out = Triple(port=True)

    # Bias and Controls
    m.pbias = h.Input(desc="100µA Pmos Bias Current")
    m.en = h.Input(desc="Enable")

    # Internal Implementation
    ## Current Mirror
    m.pdiode = Pbias(g=m.pbias, s=m.VDD33, b=m.VDD33)
    m.switch_diode = PswitchMini(g=m.VSS, s=m.pdiode.d, d=m.pbias, b=m.VDD33)
    m.psrc = MIRROR_RATIO * Pbias(g=m.pbias, s=m.VDD33, b=m.VDD33)

    ## Pmos Switches
    m.switch_a = Pswitch(g=m.inp.a, d=m.out.a, s=m.psrc.d, b=m.VDD33)
    m.switch_b = Pswitch(g=m.inp.b, d=m.out.b, s=m.psrc.d, b=m.VDD33)
    m.switch_c = Pswitch(g=m.inp.c, d=m.out.c, s=m.psrc.d, b=m.VDD33)

    ## Loads & Load Switch
    m.VVSS = h.Signal()
    m.r_a = R(r=500)(p=m.out.a, n=m.VVSS)
    m.r_b = R(r=500)(p=m.out.b, n=m.VVSS)
    m.r_c = R(r=500)(p=m.out.c, n=m.VVSS)
    m.nmos_enable = NmosV5(m=200)(g=m.en, d=m.VVSS, s=m.VSS, b=m.VSS)

    return m
