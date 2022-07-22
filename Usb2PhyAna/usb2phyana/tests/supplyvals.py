""" 
# Supply Voltage Values
"""

from typing import List, ClassVar

from pydantic.dataclasses import dataclass

# Hdl & PDK Imports
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.prefix import m


@dataclass
class SupplyVals:
    """Supply Voltage Values"""

    VDD18: h.ScalarParam
    VDDA33: h.ScalarParam

    VDD18_VALS: ClassVar[List] = [1620 * m, 1800 * m, 1980 * m]
    VDDA33_VALS: ClassVar[List] = [2970 * m, 3300 * m, 3630 * m]

    @classmethod
    def corner(cls, corner: Corner) -> "SupplyVals":
        """Create from a `Corner`"""
        idx = (
            0
            if corner == Corner.SLOW
            else 1
            if corner == Corner.TYP
            else 2
            if corner == Corner.FAST
            else None
        )
        if idx is None:
            raise ValueError
        return cls(
            VDD18=cls.VDD18_VALS[idx],
            VDDA33=cls.VDDA33_VALS[idx],
        )
