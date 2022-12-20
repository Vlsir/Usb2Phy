"""
# Injection Locked Oscillator
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21.prefix import f
from hdl21.primitives import C
from hdl21 import Pair, Diff, inverse

import s130
from s130 import MosParams

# Local Imports
from ..idac.pmos_cascode_idac import PmosIdac
from ..width import Width
from ..supplies import PhySupplies


Pmos = s130.modules.pmos
Nmos = s130.modules.nmos


@h.paramclass
class IloParams:
    cl = h.Param(dtype=h.Prefixed, desc="Capacitance Load", default=10 * f)


@h.generator
def IloInv(p: Width) -> h.Module:
    """# Injection Locked Oscillator Inverter"""

    @h.module
    class IloInv:
        # IO
        VDD, VSS = h.Ports(2)
        i = h.Input()
        o = h.Output()
        # Internal Implementation
        nmos = Nmos(MosParams(m=p.width))(g=i, d=o, s=VSS, b=VSS)
        pmos = Pmos(MosParams(m=p.width))(g=i, d=o, s=VDD, b=VDD)

    return IloInv


@h.generator
def IloStage(params: IloParams) -> h.Module:
    """
    # Injection Locked Oscillator Stage
    Note the input/ output polarities are such that the differential transfer is *non* inverting.
    """

    @h.module
    class IloStage:
        # IO
        VDD, VSS = h.Ports(2)
        inp = Diff(port=True, role=Diff.Roles.SINK)
        out = Diff(port=True, role=Diff.Roles.SOURCE)

        # Internal Implementation
        ## Forward Inverters
        fwd = Pair(IloInv(width=16))(i=inp, o=out, VDD=VDD, VSS=VSS)
        ## Cross-Coupled Output Inverters
        cross = Pair(IloInv(width=4))(i=out, o=inverse(out), VDD=VDD, VSS=VSS)
        ## Load Caps
        cl = Pair(C(c=params.cl))(p=out, n=VSS)

    return IloStage


@h.generator
def IloRing(params: IloParams) -> h.Module:
    """# ILO Ring Oscillator"""
    Ninj = Nmos(m=2)

    @h.module
    class IloRing:
        # IO
        VDD, VSS = h.Ports(2)
        inj = h.Input()

        # Internal Implementation
        stg0 = Diff(port=True, role=Diff.Roles.SOURCE)
        stg1 = Diff(port=True, role=Diff.Roles.SOURCE)
        stg2 = Diff(port=True, role=Diff.Roles.SOURCE)
        stg3 = Diff(port=True, role=Diff.Roles.SOURCE)

        ## Delay Stages
        i0 = IloStage(params)(inp=stg0, out=stg1, VDD=VDD, VSS=VSS)
        i1 = IloStage(params)(inp=stg1, out=stg2, VDD=VDD, VSS=VSS)
        i2 = IloStage(params)(inp=stg2, out=stg3, VDD=VDD, VSS=VSS)
        i3 = IloStage(params)(inp=stg3, out=inverse(stg0), VDD=VDD, VSS=VSS)

        ## Injection Nmos Switches
        n0 = Ninj(g=inj, d=stg0.p, s=stg0.n, b=VSS)
        n1 = Ninj(g=VSS, d=stg1.p, s=stg1.n, b=VSS)
        n2 = Ninj(g=VSS, d=stg2.p, s=stg2.n, b=VSS)
        n3 = Ninj(g=VSS, d=stg3.p, s=stg3.n, b=VSS)
        np0 = Ninj(g=VSS, d=stg0.p, s=VSS, b=VSS)
        np1 = Ninj(g=inj, d=stg1.p, s=VSS, b=VSS)
        np2 = Ninj(g=inj, d=stg2.p, s=VSS, b=VSS)
        np3 = Ninj(g=inj, d=stg3.p, s=VSS, b=VSS)
        nn0 = Ninj(g=VSS, d=stg0.n, s=VSS, b=VSS)
        nn1 = Ninj(g=VSS, d=stg1.n, s=VSS, b=VSS)
        nn2 = Ninj(g=VSS, d=stg2.n, s=VSS, b=VSS)
        nn3 = Ninj(g=VSS, d=stg3.n, s=VSS, b=VSS)

    return IloRing


@h.generator
def IloInner(params: IloParams) -> h.Module:
    """# Injection Locked Oscillator"""

    @h.module
    class IloInner:
        # IO
        SUPPLIES = PhySupplies(port=True)
        inj = h.Input()
        pbias = h.Input()
        fctrl = h.Input(width=5)

        # Ring stages, exposed as outputs
        stg0 = Diff(port=True, role=Diff.Roles.SOURCE)
        stg1 = Diff(port=True, role=Diff.Roles.SOURCE)
        stg2 = Diff(port=True, role=Diff.Roles.SOURCE)
        stg3 = Diff(port=True, role=Diff.Roles.SOURCE)

        # Internal Implementation
        ring_top = h.Signal()

        ## Frequency-Control Current Dac
        idac = PmosIdac()(
            ibias=pbias,
            code=fctrl,
            out=ring_top,
            VDDA33=SUPPLIES.VDD33,
            VDD18=SUPPLIES.VDD18,
            VSS=SUPPLIES.VSS,
        )

        ## Core Ring
        ring = IloRing(params)(
            inj=inj,
            stg0=stg0,
            stg1=stg1,
            stg2=stg2,
            stg3=stg3,
            VDD=ring_top,
            VSS=SUPPLIES.VSS,
        )

    return IloInner


@h.generator
def Ilo(params: IloParams) -> h.Module:
    """# Injection Locked Oscillator"""

    @h.module
    class Ilo:
        # IO
        SUPPLIES = PhySupplies(port=True)
        inj = h.Input()
        pbias = h.Input()
        fctrl = h.Input(width=5)
        sck = h.Output(desc="Serial Output Clock")

        # This level wraps the core ILO and adds the diff to single-ended level shifter
        sck_n = h.Signal()
        _stg0 = h.AnonymousBundle(p=sck, n=sck_n)
        stg1 = Diff()
        stg2 = Diff()
        stg3 = Diff()

        inner = IloInner(params)(
            fctrl=fctrl,
            inj=inj,
            pbias=pbias,
            stg0=_stg0,
            stg1=stg1,
            stg2=stg2,
            stg3=stg3,
            SUPPLIES=SUPPLIES,
        )

    return Ilo
