"""
# Rail-to-Rail, Dual Input Pair, Folded Cascode, Diff to SE Op-Amp
# and Unity-Gain Buffer using the same 
"""

import hdl21 as h
from hdl21.prefix import m
from ..tetris.mos import Nmos, Pmos


@h.paramclass
class FcascParams:
    ...  # More to come!


@h.generator
def Fcasc(params: FcascParams) -> h.Module:
    """# Rail-to-Rail, Dual Input Pair, Folded Cascode, Diff to SE Op-Amp"""

    Nbias = lambda x: Nmos(nser=8, npar=x)
    Ncasc = Nmos(nser=4)
    Pbias = lambda x: Pmos(nser=8, npar=x)
    Pcasc = Pmos(nser=4)

    @h.module
    class Fcasc:
        # IO
        VDD, VSS = h.Ports(2)
        inp = h.Diff(port=True)
        out = h.Output()
        ibias1, ibias2 = h.Inputs(2)

        # Implementation
        outn = h.Signal()
        outd = h.bundlize(p=outn, n=out)
        psd = h.Diff()
        nsd = h.Diff()
        ncascg, pcascg, pbias = h.Signals(3)

        ## Output Folded Stack
        ptop = h.Pair(Pbias(x=2))(g=outn, d=psd, s=VDD, VDD=VDD, VSS=VSS)
        pcasc = h.Pair(Pcasc)(g=pcascg, s=psd, d=outd, VDD=VDD, VSS=VSS)
        ncasc = h.Pair(Ncasc)(g=ncascg, s=nsd, d=outd, VDD=VDD, VSS=VSS)
        nbot = h.Pair(Nbias(x=2))(g=ibias1, d=nsd, s=VSS, VDD=VDD, VSS=VSS)

        ## Nmos Input Pair
        nin_bias = Nbias(x=2)(g=ibias1, s=VSS, VDD=VDD, VSS=VSS)
        nin = h.Pair(Nmos(nser=1, npar=4))(g=inp, d=psd, s=nin_bias.d, VDD=VDD, VSS=VSS)

        ## Pmos Input Pair
        pin_bias = Pbias(x=2)(g=pbias, s=VDD, VDD=VDD, VSS=VSS)
        pin = h.Pair(Pmos(nser=1, npar=4))(g=inp, d=nsd, s=pin_bias.d, VDD=VDD, VSS=VSS)

        ## Bias Tree
        ### Nmos Cascode Gate Generator, with a cheater voltage source
        ncdiode = Ncasc(g=ibias2, d=ibias2, VDD=VDD, VSS=VSS)
        ncasc_magic_vdc = h.Vdc(dc=200 * m)(p=ncdiode.s, n=VSS)
        ncascg_short = h.Vdc(dc=0)(p=ibias2, n=ncascg)

        ### Bottom Nmos Diode (with cascode)
        ndiode_casc = Ncasc(g=ncascg, d=ibias1, VDD=VDD, VSS=VSS)
        ndiode = Nbias(x=1)(g=ibias1, d=ndiode_casc.s, s=VSS, VDD=VDD, VSS=VSS)

        ### Nmos Mirror to Pmos Cascode Bias
        n1casc = Ncasc(g=ncascg, d=pcascg, VDD=VDD, VSS=VSS)
        n1src = Nbias(x=1)(g=ibias1, d=n1casc.s, s=VSS, VDD=VDD, VSS=VSS)

        ### Pmos cascode bias, with magic voltage source
        pcdiode = Pcasc(g=pcascg, d=pcascg, VDD=VDD, VSS=VSS)
        pcasc_magic_vdc = h.Vdc(dc=200 * m)(p=VDD, n=pcdiode.s)

        ### Nmos Mirror to top Pmos Bias
        n2casc = Ncasc(g=ncascg, d=pbias, VDD=VDD, VSS=VSS)
        n2src = Nbias(x=1)(g=ibias1, d=n2casc.s, s=VSS, VDD=VDD, VSS=VSS)

        ### Top Pmos Bias
        pdiode = Pbias(x=1)(g=pbias, s=VDD, VDD=VDD, VSS=VSS)
        pdiode_casc = Pcasc(s=pdiode.d, g=pcascg, d=pbias, VDD=VDD, VSS=VSS)

    return Fcasc


@h.generator
def UnityGainBuffer(params: FcascParams) -> h.Module:
    """# Rail to Rail Unity-Gain Buffer"""

    @h.module
    class UnityGainBuffer:
        # IO
        VDD, VSS = h.Ports(2)
        inp = h.Input()
        out = h.Output()
        ibias1, ibias2 = h.Inputs(2)

        # Implementation
        ## Feedback/ Stability Measurement Source
        inn = h.Signal()
        vfb = h.Vdc(dc=0)(p=out, n=inn)
        ## Core Amplifier
        amp = Fcasc(params)(
            inp=h.bundlize(p=inp, n=inn),
            out=out,
            ibias1=ibias1,
            ibias2=ibias2,
            VDD=VDD,
            VSS=VSS,
        )
        ## Load / Compensation Cap
        cl = Nmos(nser=1, npar=100)(g=out, s=VSS, d=VSS, VDD=VDD, VSS=VSS)

    return UnityGainBuffer
