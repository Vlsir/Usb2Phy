"""
# Injection Locked Oscillator
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21.prefix import f 
from hdl21.primitives import C 

import s130
from s130 import MosParams 

# Local Imports
from ...width import Width
from ...diff import Diff, inverse


# Create the default-param'ed NMOS and PMOS
PmosHvt = s130.modules.pmos_hvt
Pmos = s130.modules.pmos
Nmos = s130.modules.nmos
NmosLvt = s130.modules.nmos_lvt


@h.paramclass
class IloParams:
    cl = h.Param(dtype=h.ScalarParam, desc="Capacitance Load", default=10 * f)


@h.generator
def IloInv(p: Width) -> h.Module:
    """ # Injection Locked Oscillator Inverter """

    @h.module
    class IloInv:
        # IO
        VDD, VSS = h.Ports(2)
        i = h.Input()
        o = h.Output()
        # Internal Implementation
        nmos = Nmos(MosParams(m=p.width))(g=i, d=o, s=VSS, b=VSS)
        pmos = PmosHvt(MosParams(m=p.width))(g=i, d=o, s=VDD, b=VDD)
    
    return IloInv

@h.generator
def IloStage(params: IloParams) -> h.Module:
    """ # Injection Locked Oscillator Stage 
    Note the input/ output polarities are such that the differential 
    transfer is *non* inverting. """

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
def Ilo(params: IloParams) -> h.Module:
    """ # Injection Locked Oscillator """

    @h.module
    class Ilo:
        # IO
        VDD18, VSS = h.Ports(2)
        inj = h.Input()
        
        # Internal Implementation
        stg0 = Diff()
        stg1 = Diff()
        stg2 = Diff()
        stg3 = Diff()

        ## Delay Stages
        i0 = IloStage(params)(inp=stg0, out=stg1, VDD=VDD18, VSS=VSS)
        i1 = IloStage(params)(inp=stg1, out=stg2, VDD=VDD18, VSS=VSS)
        i2 = IloStage(params)(inp=stg2, out=stg3, VDD=VDD18, VSS=VSS)
        i3 = IloStage(params)(inp=stg3, out=inverse(stg0), VDD=VDD18, VSS=VSS)

        ## Injection Nmos Switches
        n0 = NmosLvt(MosParams())(g=inj, d=stg0.p, s=VSS, b=VSS)
        n1 = NmosLvt(MosParams())(g=inj, d=stg1.p, s=VSS, b=VSS)
        n2 = NmosLvt(MosParams())(g=inj, d=stg2.p, s=VSS, b=VSS)
        n3 = NmosLvt(MosParams())(g=inj, d=stg3.p, s=VSS, b=VSS)

    return Ilo
