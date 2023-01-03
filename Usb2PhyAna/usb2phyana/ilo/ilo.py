"""
# Injection Locked Oscillator
"""

from enum import Enum

# Hdl & PDK Imports
import hdl21 as h
from hdl21.prefix import f
from hdl21.primitives import C
from hdl21 import Pair, Diff, inverse

# Local Imports
from ..tetris.mos import Nmos
from ..logiccells import Inv
from ..idac.pmos_cascode_idac import PmosIdac
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
    Ninj = Nmos(npar=2)

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
        n0 = Ninj(g=inj, d=cko.stg0.p, s=cko.stg0.n, VSS=VSS, VDD=VDD)
        n1 = Ninj(g=VSS, d=cko.stg1.p, s=cko.stg1.n, VSS=VSS, VDD=VDD)
        n2 = Ninj(g=VSS, d=cko.stg2.p, s=cko.stg2.n, VSS=VSS, VDD=VDD)
        n3 = Ninj(g=VSS, d=cko.stg3.p, s=cko.stg3.n, VSS=VSS, VDD=VDD)
        np0 = Ninj(g=VSS, d=cko.stg0.p, s=VSS, VSS=VSS, VDD=VDD)
        np1 = Ninj(g=inj, d=cko.stg1.p, s=VSS, VSS=VSS, VDD=VDD)
        np2 = Ninj(g=inj, d=cko.stg2.p, s=VSS, VSS=VSS, VDD=VDD)
        np3 = Ninj(g=inj, d=cko.stg3.p, s=VSS, VSS=VSS, VDD=VDD)
        nn0 = Ninj(g=VSS, d=cko.stg0.n, s=VSS, VSS=VSS, VDD=VDD)
        nn1 = Ninj(g=VSS, d=cko.stg1.n, s=VSS, VSS=VSS, VDD=VDD)
        nn2 = Ninj(g=VSS, d=cko.stg2.n, s=VSS, VSS=VSS, VDD=VDD)
        nn3 = Ninj(g=VSS, d=cko.stg3.n, s=VSS, VSS=VSS, VDD=VDD)

    return IloRing


@h.generator
def IloInner(params: IloParams) -> h.Module:
    """# Injection Locked Oscillator"""

    @h.module
    class IloInner:
        # IO
        SUPPLIES = PhySupplies(port=True)
        inj = h.Input(desc="Injection Input")
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
            cko=h.bundlize(
                stg0=stg0,
                stg1=stg1,
                stg2=stg2,
                stg3=stg3,
            ),
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
        inj = h.Input(desc="Injection Input")
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
