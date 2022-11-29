"""
# Slicer

FIXME: sizing of all transistors, all of which are thus far default values.
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21 import Diff, Pair

import s130
from s130 import MosParams

# Create the default-param'ed NMOS and PMOS
Pmos = s130.modules.pmos(MosParams())
Nmos = s130.modules.nmos_lvt(MosParams())


@h.generator
def Slicer(_: h.HasNoParams) -> h.Module:
    """# StrongArm Based Slicer Generator"""

    @h.module
    class Nor2:
        """# Nor2 for SR Latch
        Inputs `i` and `fb` are designated for input and feedback respectively.
        The feedback input is the faster of the two."""

        # IO
        VDD18, VSS = h.Ports(2)
        i, fb = h.Inputs(2)
        z = h.Output()

        # Internal Implementation
        pi = Pmos(g=i, s=VDD18, b=VDD18)
        pfb = Pmos(g=fb, d=z, s=pi.d, b=VDD18)
        nfb = Nmos(g=fb, d=z, s=VSS, b=VSS)
        ni = Nmos(g=i, d=z, s=VSS, b=VSS)

    @h.module
    class SrLatch:
        """# Nor2-Based SR Latch"""

        # IO
        VDD18, VSS = h.Ports(2)
        inp = Diff(port=True, role=Diff.Roles.SINK)
        out = Diff(port=True, role=Diff.Roles.SOURCE)

        # Internal Implementation
        ## Pair of cross-coupled Nor2
        norp = Nor2(i=inp.p, z=out.n, fb=out.p, VDD18=VDD18, VSS=VSS)
        norn = Nor2(i=inp.n, z=out.p, fb=out.n, VDD18=VDD18, VSS=VSS)

    @h.module
    class StrongArm:
        """# StrongArm Comparator"""

        # IO
        VDD18, VSS = h.Ports(2)
        inp = Diff(port=True, role=Diff.Roles.SINK)
        out = Diff(port=True, role=Diff.Roles.SOURCE)
        clk = h.Input()

        # Internal Implementation
        cross = Diff(desc="Cross-coupled net-pair")
        ## Clock Nmos
        nclk = Nmos(g=clk, s=VSS, b=VSS)
        ## Input Pair
        ninp = Nmos(g=inp.p, s=nclk.d, b=VSS)
        ninn = Nmos(g=inp.n, s=nclk.d, b=VSS)
        ## Latch Nmos
        nlatp = Nmos(g=cross.p, d=cross.n, s=ninp.d, b=VSS)
        nlatn = Nmos(g=cross.n, d=cross.p, s=ninn.d, b=VSS)
        ## Latch Pmos
        platp = Pmos(g=cross.p, d=cross.n, s=VDD18, b=VDD18)
        platn = Pmos(g=cross.n, d=cross.p, s=VDD18, b=VDD18)
        ## Reset Pmos
        prstp = Pmos(g=clk, d=cross.p, s=VDD18, b=VDD18)
        prstn = Pmos(g=clk, d=cross.n, s=VDD18, b=VDD18)
        ## Output Inverters
        pinvp = Pmos(g=cross.p, d=out.n, s=VDD18, b=VDD18)
        ninvp = Nmos(g=cross.p, d=out.n, s=VSS, b=VSS)
        pinvn = Pmos(g=cross.n, d=out.p, s=VDD18, b=VDD18)
        ninvn = Nmos(g=cross.n, d=out.p, s=VSS, b=VSS)

    @h.module
    class Slicer:
        """# StrongArm Based Slicer"""

        # IO
        VDD18, VSS = h.Ports(2)
        inp = Diff(port=True, role=Diff.Roles.SINK)
        out = Diff(port=True, role=Diff.Roles.SOURCE)
        clk = h.Input()

        # Internal Implementation
        sout = Diff()
        ## StrongArm Comparator
        sa = StrongArm(inp=inp, out=sout, clk=clk, VDD18=VDD18, VSS=VSS)
        ## SR Latch
        sr = SrLatch(inp=sout, out=out, VDD18=VDD18, VSS=VSS)

    return Slicer
