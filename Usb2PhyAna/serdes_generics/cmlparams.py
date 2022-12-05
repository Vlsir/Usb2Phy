# Hdl & PDK Imports
import hdl21 as h


@h.paramclass
class CmlParams:
    """CML Parameters"""

    rl = h.Param(dtype=h.Prefixed, desc="Load Res Value (Ohms)")
    cl = h.Param(dtype=h.Prefixed, desc="Load Cap Value (F)")
    ib = h.Param(dtype=h.Prefixed, desc="Bias Current Value (A)")
