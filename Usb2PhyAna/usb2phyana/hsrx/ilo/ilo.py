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
from ...idac.pmos_cascode_idac import PmosIdac
from ...width import Width


PmosHvt = s130.modules.pmos_hvt
Pmos = s130.modules.pmos
Nmos = s130.modules.nmos
NmosLvt = s130.modules.nmos_lvt

Pbias = Pmos(MosParams(w=1, l=1, m=100))


@h.paramclass
class IloParams:
    cl = h.Param(dtype=h.ScalarParam, desc="Capacitance Load", default=10 * f)


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
        fwdp = IloInv(width=16)(i=inp.p, o=out.n, VDD=VDD, VSS=VSS)
        fwdn = IloInv(width=16)(i=inp.n, o=out.p, VDD=VDD, VSS=VSS)
        ## Cross-Coupled Output Inverters
        crossp = IloInv(width=4)(i=out.p, o=out.n, VDD=VDD, VSS=VSS)
        crossn = IloInv(width=4)(i=out.n, o=out.p, VDD=VDD, VSS=VSS)
        ## Load Caps
        clp = C(C.Params(c=params.cl))(p=out.p, n=VSS)
        cln = C(C.Params(c=params.cl))(p=out.n, n=VSS)

    return IloStage


@h.generator
def IloRing(params: IloParams) -> h.Module:
    """# ILO Ring Oscillator"""

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
        n0 = NmosLvt(MosParams())(g=inj, d=stg0.p, s=VSS, b=VSS)
        n1 = NmosLvt(MosParams())(g=inj, d=stg1.p, s=VSS, b=VSS)
        n2 = NmosLvt(MosParams())(g=inj, d=stg2.p, s=VSS, b=VSS)
        n3 = NmosLvt(MosParams())(g=inj, d=stg3.p, s=VSS, b=VSS)

    return IloRing


@h.generator
def Ilo(params: IloParams) -> h.Module:
    """# Injection Locked Oscillator"""

    @h.module
    class Ilo:
        # IO
        VDDA33, VDD18, VSS = h.Ports(3)
        inj = h.Input()
        pbias = h.Input()
        fctrl = h.Input(width=5)

        # Internal Implementation
        stg0 = Diff(port=True, role=Diff.Roles.SOURCE)
        stg1 = Diff(port=True, role=Diff.Roles.SOURCE)
        stg2 = Diff(port=True, role=Diff.Roles.SOURCE)
        stg3 = Diff(port=True, role=Diff.Roles.SOURCE)
        ring_top = h.Signal()

        ## Frequency-Control Current Dac
        idac = PmosIdac()(
            ibias=pbias, code=fctrl, out=ring_top, VDDA33=VDDA33, VDD18=VDD18, VSS=VSS
        )

        ## Core Ring
        ring = IloRing(params)(
            inj=inj, stg0=stg0, stg1=stg1, stg2=stg2, stg3=stg3, VDD=ring_top, VSS=VSS
        )

    return Ilo
