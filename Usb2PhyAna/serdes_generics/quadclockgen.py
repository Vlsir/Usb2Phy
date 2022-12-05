""" 
# Quadrature Clock Generator 

For simulation, from ideal pulse voltage sources 
"""

# Hdl & PDK Imports
import hdl21 as h
from hdl21.primitives import Vpulse

# Local Imports
from ..quadclock import QuadClock


@h.paramclass
class QclkParams:
    """Quadrature Clock Generator Parameters"""

    period = h.Param(dtype=h.Prefixed, desc="Period")
    v1 = h.Param(dtype=h.Prefixed, desc="Low Voltage Level")
    v2 = h.Param(dtype=h.Prefixed, desc="High Voltage Level")
    trf = h.Param(dtype=h.Prefixed, desc="Rise / Fall Time")


@h.generator
def QuadClockGen(p: QclkParams) -> h.Module:
    """# Quadrature Clock Generator
    For simulation, from ideal pulse voltage sources"""

    def phpars(idx: int) -> Vpulse.Params:
        """Closure to create the delay-value for quadrature index `idx`, valued 0-3.
        Transitions start at 1/8 of a period, so that clocks are stable during time zero."""

        # Delays per phase, in eights of a period.
        # Note the negative values set `val2` as active during simulation time zero.
        vals = [1, 3, -3, -1]
        if idx < 0 or idx > 3:
            raise ValueError

        return Vpulse.Params(
            v1=p.v1,
            v2=p.v2,
            period=p.period,
            rise=p.trf,
            fall=p.trf,
            width=p.period / 2 - p.trf,
            delay=vals[idx] * p.period / 8 - p.trf / 2,
        )

    ckg = h.Module()
    ckg.VSS = VSS = h.Port()

    ckg.ckq = ckq = QuadClock(
        role=QuadClock.Roles.SINK, port=True, desc="Quadrature Clock Output"
    )
    ckg.v0 = Vpulse(phpars(0))(p=ckq.ck0, n=VSS)
    ckg.v90 = Vpulse(phpars(1))(p=ckq.ck90, n=VSS)
    ckg.v180 = Vpulse(phpars(2))(p=ckq.ck180, n=VSS)
    ckg.v270 = Vpulse(phpars(3))(p=ckq.ck270, n=VSS)
    return ckg
