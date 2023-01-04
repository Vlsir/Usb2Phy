import hdl21 as h
from hdl21.pdk import Corner


@h.paramclass
class Pvt:
    """Process, Voltage, and Temperature Condition"""

    p = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    v = h.Param(dtype=Corner, desc="Voltage Corner", default=Corner.TYP)
    t = h.Param(dtype=Corner, desc="Temperature Corner", default=Corner.TYP)

    def __repr__(self) -> str:
        return f"Pvt({self.p}, {self.v}, {self.t})"


class Project:
    """
    # Project-Level Settings
    Generally retrieves values per `Corner`.
    """

    @staticmethod
    def temper(corner: Corner) -> int:
        vals = {Corner.SLOW: -25, Corner.TYP: 25, Corner.FAST: 75}
        return vals[corner]
