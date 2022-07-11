"""
# Injection Locked Oscillator
"""

# Hdl & PDK Imports
import hdl21 as h

import s130
from s130 import MosParams 

# Local Imports
from ...width import Width
from ...diff import Diff, inverse


# Create the default-param'ed NMOS and PMOS
Pmos = s130.modules.pmos
NmosLvt = s130.modules.nmos_lvt


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
        nmos = NmosLvt(MosParams(m=p.width))(g=i, d=o, s=VSS, b=VSS)
        pmos = Pmos(MosParams(m=p.width))(g=i, d=o, s=VDD, b=VDD)
    
    return IloInv


@h.module
class IloStage:
    """ # Injection Locked Oscillator Stage 
    Note the input/ output polarities are such that the differential 
    transfer is *non* inverting. """

    # IO
    VDD, VSS = h.Ports(2)
    inp = Diff(port=True, role=Diff.Roles.SINK)
    out = Diff(port=True, role=Diff.Roles.SOURCE)

    # Internal Implementation
    fwdp = IloInv(width=8)(i=inp.p, o=out.n, VDD=VDD, VSS=VSS)
    fwdn = IloInv(width=8)(i=inp.n, o=out.p, VDD=VDD, VSS=VSS)
    crossp = IloInv(width=2)(i=out.p, o=out.n, VDD=VDD, VSS=VSS)
    crossn = IloInv(width=2)(i=out.n, o=out.p, VDD=VDD, VSS=VSS)


@h.module
class Ilo:
    """ # Injection Locked Oscillator """

    # IO
    VDD18, VSS = h.Ports(2)
    inj = h.Input()
    
    # Internal Implementation
    stg0 = Diff()
    stg1 = Diff()
    stg2 = Diff()
    stg3 = Diff()

    ## Delay Stages
    i0 = IloStage(inp=stg0, out=stg1, VDD=VDD18, VSS=VSS)
    i1 = IloStage(inp=stg1, out=stg2, VDD=VDD18, VSS=VSS)
    i2 = IloStage(inp=stg2, out=stg3, VDD=VDD18, VSS=VSS)
    i3 = IloStage(inp=stg3, out=inverse(stg0), VDD=VDD18, VSS=VSS)

    ## Injection Nmos Switches
    n0 = NmosLvt(MosParams())(g=inj, d=stg0.p, s=VSS, b=VSS)
    n1 = NmosLvt(MosParams())(g=inj, d=stg1.p, s=VSS, b=VSS)
    n2 = NmosLvt(MosParams())(g=inj, d=stg2.p, s=VSS, b=VSS)
    n3 = NmosLvt(MosParams())(g=inj, d=stg3.p, s=VSS, b=VSS)

