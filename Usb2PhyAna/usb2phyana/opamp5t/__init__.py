"""
# "5T" Op-Amp Generator
"""

import hdl21 as h


@h.paramclass
class Params:
    """# 5T Op-Amp Parameters"""

    load = h.Param(dtype=h.Instantiable, desc="Load Mos Device")
    inp = h.Param(dtype=h.Instantiable, desc="Input Mos Device")
    bias = h.Param(dtype=h.Instantiable, desc="Bias Device")
    mostype = h.Param(dtype=h.MosType, desc="Mos Input Type", default=h.MosType.NMOS)


@h.generator
def OpAmp5T(params: Params) -> h.Module:
    """# "5T" Op-Amp Generator"""

    if params.mostype == h.MosType.NMOS:
        return NmosOpAmp5T(params)
    return PmosOpAmp5T(params)


@h.generator
def NmosOpAmp5T(params: Params) -> h.Module:
    """# "5T" Nmos-Input Op-Amp Generator"""

    @h.module
    class NmosOpAmp5T:
        # IO
        VDD, VSS = h.Ports(2)
        inp = h.Diff(port=True)
        out = h.Output()
        ibias = h.Input()

        # Implementation
        ## Internal Signals
        outn, cs = h.Signals(2)
        outd = h.bundlize(p=outn, n=out)
        biasd = h.bundlize(p=ibias, n=cs)

        ## Bias Mirror Pair
        bias_pair = h.Pair(params.bias)(g=ibias, d=biasd, s=VSS, VSS=VSS, VDD=VDD)
        ## Input Pair
        inp_pair = h.Pair(params.inp)(g=inp, d=outd, s=cs, VSS=VSS, VDD=VDD)
        ## Load Current-Mirror Pair
        load_pair = h.Pair(params.load)(g=outn, d=outd, s=VDD, VSS=VSS, VDD=VDD)

    return NmosOpAmp5T


@h.generator
def PmosOpAmp5T(params: Params) -> h.Module:
    """# "5T" Pmos-Input Op-Amp Generator"""
    # FIXME! a straightforward swap of the `load_pair` and `bias_pair` sources!
    raise NotImplementedError
