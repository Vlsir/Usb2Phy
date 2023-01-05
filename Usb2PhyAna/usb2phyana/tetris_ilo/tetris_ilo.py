"""
# Injection Locked Oscillator
"""

from enum import Enum

# Hdl & PDK Imports
import hdl21 as h
from hdl21.prefix import f, K, PICO
from hdl21.primitives import C
from hdl21 import Pair, Diff, inverse

# Local Imports
from ..tetris.mos import Nmos
from ..logiccells import Inv
from ..idac.tetris_pmos_idac import PmosIdac
from ..supplies import PhySupplies


@h.bundle
class OctalClock:
    """# Octal Clock
    Eight stages comprised of four differential pairs."""

    class Roles(Enum):
        # Clock roles: source or sink
        SOURCE = "SOURCE"
        SINK = "SINK"

    # The four quadrature phases, all driven by SOURCE and consumed by SINK.
    stg0 = h.Diff(src=Roles.SOURCE, dest=Roles.SINK)
    stg1 = h.Diff(src=Roles.SOURCE, dest=Roles.SINK)
    stg2 = h.Diff(src=Roles.SOURCE, dest=Roles.SINK)
    stg3 = h.Diff(src=Roles.SOURCE, dest=Roles.SINK)


@h.paramclass
class IloParams:
    cl = h.Param(dtype=h.Prefixed, desc="Capacitance Load", default=10 * f)


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
        fwd = Pair(Inv(x=16))(i=inp, z=out, VDD=VDD, VSS=VSS)
        ## Cross-Coupled Output Inverters
        cross = Pair(Inv(x=4))(i=out, z=inverse(out), VDD=VDD, VSS=VSS)
        ## Load Caps
        cl = Pair(C(c=params.cl))(p=out, n=VSS)

    return IloStage


@h.generator
def IloRing(params: IloParams) -> h.Module:
    """# ILO Ring Oscillator"""
    Ninj = Nmos(npar=16)

    @h.module
    class IloRing:
        # IO
        VDD, VSS = h.Ports(2)
        inj = h.Input(desc="Injection Input")
        cko = OctalClock(port=True, role=OctalClock.Roles.SOURCE)

        # Internal Implementation
        ## Delay Stages
        i0 = IloStage(params)(inp=cko.stg0, out=cko.stg1, VDD=VDD, VSS=VSS)
        i1 = IloStage(params)(inp=cko.stg1, out=cko.stg2, VDD=VDD, VSS=VSS)
        i2 = IloStage(params)(inp=cko.stg2, out=cko.stg3, VDD=VDD, VSS=VSS)
        i3 = IloStage(params)(inp=cko.stg3, out=inverse(cko.stg0), VDD=VDD, VSS=VSS)

        ## Injection Nmos Switches
        # n0 = Ninj(g=inj, d=cko.stg0.p, s=cko.stg0.n, VSS=VSS, VDD=VDD)
        # n1 = Ninj(g=VSS, d=cko.stg1.p, s=cko.stg1.n, VSS=VSS, VDD=VDD)
        # n2 = Ninj(g=VSS, d=cko.stg2.p, s=cko.stg2.n, VSS=VSS, VDD=VDD)
        # n3 = Ninj(g=VSS, d=cko.stg3.p, s=cko.stg3.n, VSS=VSS, VDD=VDD)
        np0 = Ninj(g=inj, d=cko.stg0.p, s=VSS, VSS=VSS, VDD=VDD)
        np1 = Ninj(g=inj, d=cko.stg1.p, s=VSS, VSS=VSS, VDD=VDD)
        np2 = Ninj(g=inj, d=cko.stg2.p, s=VSS, VSS=VSS, VDD=VDD)
        np3 = Ninj(g=inj, d=cko.stg3.p, s=VSS, VSS=VSS, VDD=VDD)
        nn0 = Ninj(g=VSS, d=cko.stg0.n, s=VSS, VSS=VSS, VDD=VDD)
        nn1 = Ninj(g=VSS, d=cko.stg1.n, s=VSS, VSS=VSS, VDD=VDD)
        nn2 = Ninj(g=VSS, d=cko.stg2.n, s=VSS, VSS=VSS, VDD=VDD)
        nn3 = Ninj(g=VSS, d=cko.stg3.n, s=VSS, VSS=VSS, VDD=VDD)

    return IloRing


@h.generator
def IloLevelShifters(params: IloParams) -> h.Module:
    """# Injection Locked Oscillator"""

    @h.module
    class IloLevelShifters:
        SUPPLIES = PhySupplies(port=True)
        inp = OctalClock(port=True)
        out = OctalClock(port=True)

        i0 = IloDiffLevelShift(params)(inp=inp.stg0, out=out.stg0, SUPPLIES=SUPPLIES)
        i1 = IloDiffLevelShift(params)(inp=inp.stg1, out=out.stg1, SUPPLIES=SUPPLIES)
        i2 = IloDiffLevelShift(params)(inp=inp.stg2, out=out.stg2, SUPPLIES=SUPPLIES)
        i3 = IloDiffLevelShift(params)(inp=inp.stg3, out=out.stg3, SUPPLIES=SUPPLIES)

    return IloLevelShifters


@h.generator
def IloDiffLevelShift(params: IloParams) -> h.Module:
    """# Differential Level Shifter"""

    @h.module
    class IloDiffLevelShift:
        ## IO Interface
        SUPPLIES = PhySupplies(port=True)
        inp = Diff(port=True)
        out = Diff(port=True)

        ## Implementation
        mid = Diff()
        acpair = Pair(IloAcLevelShift(params))(
            inp=inp, out=mid, VDD18=SUPPLIES.VDD18, VSS=SUPPLIES.VSS
        )
        outstg = Pair(Inv(x=8))(i=mid, z=out, VDD=SUPPLIES.VDD18, VSS=SUPPLIES.VSS)
        # outstg = IloStage(params)(
        #     inp=mid, out=out, VDD=SUPPLIES.VDD18, VSS=SUPPLIES.VSS
        # )

    return IloDiffLevelShift


@h.generator
def IloAcLevelShift(params: IloParams) -> h.Module:
    """# Single-Ended AC Level Shifter"""

    @h.module
    class IloAcLevelShift:
        ## IO Interface
        VDD18, VSS = h.Ports(2)
        inp = h.Input()
        out = h.Output()

        ## Implementation
        g = h.Signal()
        cac = h.Cap(c=1 * PICO)(p=inp, n=g)
        inv = Inv(x=16)(i=g, z=out, VDD=VDD18, VSS=VSS)
        rfb = h.Res(r=100 * K)(p=out, n=g)

    return IloAcLevelShift


@h.generator
def Ilo(params: IloParams) -> h.Module:
    """# Injection Locked Oscillator"""

    @h.module
    class Ilo:
        # IO
        SUPPLIES = PhySupplies(port=True)
        inj = h.Input(desc="Injection Input")
        pbias = h.Input()
        fctrl = h.Input(width=5)
        cko = OctalClock(port=True)

        # Internal Implementation
        ring_top = h.Signal()

        ## Frequency-Control Current Dac
        idac = PmosIdac()(
            ibias=pbias,
            code=fctrl,
            # out=ring_top,
            VDD18=SUPPLIES.VDD18,
            VSS=SUPPLIES.VSS,
        )
        ## DAC Output Current Sense
        visns = h.Vdc(dc=0)(p=idac.out, n=ring_top)

        ## Core Ring
        ring = IloRing(params)(
            inj=inj,
            VDD=ring_top,
            VSS=SUPPLIES.VSS,
        )

        ## Output Level Shifters
        ls = IloLevelShifters(params)(
            inp=ring.cko,
            out=cko,
            SUPPLIES=SUPPLIES,
        )

    return Ilo
