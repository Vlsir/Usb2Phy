"""
# Slicer
"""

# Hdl & PDK Imports
import hdl21 as h

import s130
from s130 import MosParams 

# Local Imports
from ...diff import Diff

# Create the default-param'ed NMOS and PMOS
Pmos = s130.modules.pmos(MosParams())
Nmos = s130.modules.nmos_lvt(MosParams())


@h.module
class Slicer:
    """ # StrongArm Slicer """

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
    ninvp = Pmos(g=cross.p, d=out.n, s=VSS, b=VSS)
    pinvn = Pmos(g=cross.n, d=out.p, s=VDD18, b=VDD18)
    ninvn = Pmos(g=cross.n, d=out.p, s=VSS, b=VSS)
