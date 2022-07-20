# Hdl & PDK Imports
import hdl21 as h


@h.paramclass
class CmlParams:
    """CML Parameters"""

    rl = h.Param(dtype=h.ScalarParam, desc="Load Res Value (Ohms)")
    cl = h.Param(dtype=h.ScalarParam, desc="Load Cap Value (F)")
    ib = h.Param(dtype=h.ScalarParam, desc="Bias Current Value (A)")
