"""
# Widely re-used `SimOptions`
"""

from pathlib import Path
from vlsirtools.spice import SimOptions, SupportedSimulators, ResultFormat

sim_options = SimOptions(
    rundir=None,  ## FIXME: specifying directories for lots of parallel sims Path("./scratch"),
    fmt=ResultFormat.SIM_DATA,
    simulator=SupportedSimulators.SPECTRE,
)
