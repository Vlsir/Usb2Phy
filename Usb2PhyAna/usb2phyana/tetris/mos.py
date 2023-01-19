"""
# "Tetris" Mos-Stack Module Generators
"""

from dataclasses import replace

import hdl21 as h
from hdl21.prefix import n
from hdl21.generators import Nmos as NmosGen, Pmos as PmosGen, MosParams as GenMosParams


@h.paramclass
class TetrisMosParams:
    """# Tetris Mos Stack Parameters"""

    nser = h.Param(dtype=int, desc="Number of series fingers", default=1)
    npar = h.Param(dtype=int, desc="Number of parallel stacks", default=1)


# The single device size gets encoded right here:
NMOS_PARAMS = GenMosParams(
    w=820 * n,
    l=150 * n,
    vth=h.MosVth.STD,
)
PMOS_PARAMS = GenMosParams(
    w=820 * n,
    l=150 * n,
    vth=h.MosVth.HIGH,
)
DUMMY_PARAMS = GenMosParams(
    w=420 * n,
    l=150 * n,
)


@h.generator
def Nmos(params: TetrisMosParams) -> h.Module:
    """# Nmos Module Generator"""

    if params.nser not in (1, 2, 4, 8, 16, 32, 64):
        msg = f"Invalid {params} must be (1, 2, 4, 8, or 16) series instances"
        raise ValueError(msg)

    # Series-stack our Nmos by replacing its `nser` param
    n = NmosGen(replace(NMOS_PARAMS, nser=params.nser, npar=params.npar))
    # And similarly create our dummy Pmos by replacing its `npar` param
    p = PmosGen(
        replace(DUMMY_PARAMS, vth=h.MosVth.HIGH, nser=1, npar=params.nser * params.npar)
    )

    # Create our module which instantiates them
    m = module_inner()
    # Connect our primary device
    m.n = n(d=m.d, g=m.g, s=m.s, b=m.VSS)
    # And its paired dummy friend
    m.p = p(d=m.VDD, g=m.VDD, s=m.VDD, b=m.VDD)

    return m


@h.generator
def Pmos(params: TetrisMosParams) -> h.Module:
    """# Pmos Module Generator"""

    if params.nser not in (1, 2, 4, 8, 16, 32, 64):
        msg = f"Invalid {params} must be (1, 2, 4, 8, or 16) series instances"
        raise ValueError(msg)

    # Series-stack our Pmos by replacing its `nser` param
    p = PmosGen(replace(PMOS_PARAMS, nser=params.nser, npar=params.npar))
    # And similarly create our dummy Nmos by replacing its `npar` param
    n = NmosGen(
        replace(DUMMY_PARAMS, vth=h.MosVth.STD, nser=1, npar=params.nser * params.npar)
    )

    # Create our module which instantiates them
    m = module_inner()
    # Connect our primary device
    m.p = p(d=m.d, g=m.g, s=m.s, b=m.VDD)
    # And its paired dummy friend
    m.n = n(d=m.VSS, g=m.VSS, s=m.VSS, b=m.VSS)

    return m


def module_inner() -> h.Module:
    """Inner helper function to create Mos modules
    Primarily creates the module and declares its IO.
    Note this *is not* an Hdl21 generator, as its output is intended to be further modified."""

    # Create our module which instantiates them
    m = h.Module()
    # Primary transistor IOs
    m.d, m.g, m.s = h.Inouts(3)
    # Supplies
    m.VDD, m.VSS = h.Inouts(2)
    return m


__all__ = ["Nmos", "Pmos", "TetrisMosParams"]
