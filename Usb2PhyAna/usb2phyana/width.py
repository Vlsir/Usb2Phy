# Std-Lib Imports
from typing import Dict
from enum import Enum, auto

# Hdl & PDK Imports
import hdl21 as h


@h.paramclass
class Width:
    """ Parameter class for Generators with a single integer-valued `width` parameter. """

    width = h.Param(dtype=int, desc="Parametric Width", default=1)
