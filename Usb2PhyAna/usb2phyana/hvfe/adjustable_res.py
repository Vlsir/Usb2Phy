"""
Adjustable Resistor Generator
"""


import hdl21 as h
from hdl21.primitives import MosParams, PhysicalResistorParams


@h.paramclass
class AdjustableResParams:
    """ Parameters for the Adjustable Resistors """
    mos_params = h.Param(dtype=MosParams, desc="Transistor Params")
    res_params = h.Param(dtype=PhysicalResistorParams, desc="Resistor Params")
    nmos = h.Param(dtype=bool, desc="True if NMOS Switch Device", default=True)
    num_units = h.Param(
        dtype=int, desc="Number of Units in Parallel", default=1)


@h.generator
def AdjustableResUnit(p: AdjustableResParams) -> h.Module:

    m = h.Module()
    m.out = h.Output()
    m.mid = h.Signal()
    if p.nmos:
        m.VSS = sup = h.Port()
        m.en = h.Input()
        m.switch = h.Nmos(p.mos_params)(
            g=m.en, d=m.mid, s=m.VSS, b=m.VSS)
    else:
        m.VDD = sup = h.Port()
        m.enb = h.Input()
        m.switch = h.Pmos(p.mos_params)(
            g=m.enb, d=m.mid, s=m.VDD,  b=m.VDD)

    m.res = h.PhysicalResistor(p.res_params)(
        p=m.out, n=m.mid, b=sup)

    return m


@h.generator
def AdjustableRes(p: AdjustableResParams) -> h.Module:
    m = h.Module()
    m.out = h.Output()
    if p.nmos:
        m.VSS = h.Port()
        m.ctrl = h.Input(width=p.num_units)
        for i in range(p.num_units):
            setattr(m, f"runit_{i}", AdjustableResUnit(p)(
                out=m.out, en=m.ctrl[i], VSS=m.VSS))
    else:
        m.VDD = h.Port()
        m.ctrlb = h.Input(width=p.num_units)
        for i in range(p.num_units):
            setattr(m, f"runit_{i}", AdjustableResUnit(p)(
                out=m.out, enb=m.ctrlb[i], VDD=m.VDD))

    return m

