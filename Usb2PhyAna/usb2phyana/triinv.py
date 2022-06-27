"""
# Custom Tri-State Inverter 
"""

# Hdl & PDK Imports
import hdl21 as h
import s130
from s130 import MosParams

NmosLvt = s130.modules.nmos_lvt
Pmos = s130.modules.pmos

# Local Imports
from .width import Width


@h.generator
def TriInv(p: Width) -> h.Module:
    """ Tri-State Inverter """

    m = h.Module()
    m.VDD, m.VSS = h.Ports(2)
    m.i, m.en = h.Inputs(2)
    m.z = h.Output()
    m.enb = h.Signal()

    # Enable inversion inverter
    m.pinv = Pmos(MosParams(w=1, m=1))(d=m.enb, g=m.en, s=m.VDD, b=m.VDD)
    m.ninv = NmosLvt(MosParams(w=1, m=1))(d=m.enb, g=m.en, s=m.VSS, b=m.VSS)

    # Main Tristate Inverter
    m.pi = Pmos(MosParams(w=2, m=p.width))(g=m.i, s=m.VDD, b=m.VDD)
    m.pe = Pmos(MosParams(w=2, m=p.width))(d=m.z, g=m.enb, s=m.pi.d, b=m.VDD)
    m.ne = NmosLvt(MosParams(w=1, m=p.width))(d=m.z, g=m.en, b=m.VSS)
    m.ni = NmosLvt(MosParams(w=1, m=p.width))(d=m.ne.s, g=m.i, s=m.VSS, b=m.VSS)

    return m
