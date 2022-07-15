"""
# CML Ring Oscillator
"""

# Hdl & PDK Imports
import hdl21 as h
import s130
from s130 import MosParams

# Local Imports
from ..diff import Diff, inverse
from ..cmlparams import CmlParams


NmosLvt = s130.modules.nmos_lvt
Cap = h.primitives.Cap
Res = h.primitives.Res

# Define a few reused device-parameter combos
Nswitch = NmosLvt(MosParams(m=10))
Nbias = NmosLvt(MosParams(w=1, l=1, m=100))


@h.generator
def CmlStage(params: CmlParams) -> h.Module:
    """ # CML Delay Buffer """

    @h.module
    class CmlStage:
        # IO Interface
        VDD, VSS = h.Ports(2)

        ## Differential Input & Output
        i = Diff(port=True, role=Diff.Roles.SINK)
        o = Diff(port=True, role=Diff.Roles.SOURCE)
        
        ## Gate Bias for Current Sources
        bias = h.Input()

        # Internal Implementation

        ## Load Resistors
        rlp = Res(Res.Params(r=params.rl))(p=o.p, n=VDD)
        rln = Res(Res.Params(r=params.rl))(p=o.n, n=VDD)
        ## Load Caps
        clp = Cap(Cap.Params(c=params.cl))(p=o.p, n=VDD)
        cln = Cap(Cap.Params(c=params.cl))(p=o.n, n=VDD)
        ## Current Bias
        ni = Nbias(g=bias, s=VSS, b=VSS)
        ## Input Pair
        ndp = Nswitch(s=ni.d, g=i.p, d=o.n, b=VSS)
        ndn = Nswitch(s=ni.d, g=i.n, d=o.p, b=VSS)

    return CmlStage


@h.generator
def CmlRo(params: CmlParams) -> h.Module:
    """ # CML Ring Oscillator """

    @h.module
    class CmlRo:
        # IO Interface
        VDD, VSS = h.Ports(2)
        ## Bias input and gate
        ibias = h.Input(desc="Current Bias Input")

        # Internal Implementation
        stg0 = Diff()
        stg1 = Diff()
        stg2 = Diff()
        stg3 = Diff()

        ## Delay Stages
        i0 = CmlStage(params)(i=stg0, o=stg1, bias=ibias, VDD=VDD, VSS=VSS)
        i1 = CmlStage(params)(i=stg1, o=stg2, bias=ibias, VDD=VDD, VSS=VSS)
        i2 = CmlStage(params)(i=stg2, o=stg3, bias=ibias, VDD=VDD, VSS=VSS)
        i3 = CmlStage(params)(i=stg3, o=inverse(stg0), bias=ibias, VDD=VDD, VSS=VSS)

        ## Current-Bias Transistor
        nb = Nbias(g=ibias, d=ibias, s=VSS, b=VSS)

    return CmlRo
