"""
# Testbench Utilities
"""

# Std-Lib Imports
from copy import copy
from pathlib import Path
from typing import Sequence

# PyPi Imports
import numpy as np
import matplotlib.pyplot as plt

# Hdl & PDK Imports
import sitepdks as _
import s130
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.sim import Sim, LinearSweep, SaveMode
from hdl21.prefix import m, n
from vlsirtools.spice.sim_data import SimResult

# Local Imports
from ...tests.sim_options import sim_options


@h.paramclass
class TbParams:
    corner = h.Param(dtype=Corner, desc="Process Corner", default=Corner.TYP)
    VDD = h.Param(dtype=h.Prefixed, desc="Supply Voltage Value", default=1800 * m)
    temper = h.Param(dtype=int, desc="Simulation Temperature (C)", default=25)
    code = h.Param(dtype=int, desc="PI Code", default=11)


def sim_input(tb: h.Instantiable, params: TbParams) -> Sim:
    """Phase Interpolator Delay Sim"""

    print(f"Simulating PhaseInterp for code {params.code}")

    # Craft our simulation stimulus
    sim = Sim(tb=tb, attrs=s130.install.include(params.corner))
    sim.tran(tstop=10 * n)

    # FIXME: eventually this can be a simulator-internal `Sweep`
    # p = sim.param(name="code", val=0)
    # sim.sweepanalysis(inner=[tr], var=p, sweep=LinearSweep(0, 1, 2), name="mysweep")
    # sim.save(SaveMode.ALL)
    # sim.meas(analysis=tr, name="a_delay", expr="trig_targ_vcode")

    # The delay measurement
    sim.literal(
        f"""
        simulator lang=spice
        .temp {params.temper}
        .measure tran tdelay when 'V(xtop:dck_p)-V(xtop:dck_n)'=0 rise=2 td=3n
        .option autostop
        simulator lang=spectre
    """
    )

    sim.include(s130.resources / "stdcells.sp")

    # FIXME: handling of multi-directory sims
    # opts = copy(sim_options)
    # opts.rundir = Path(f"./scratch/code{params.code}")

    return sim


def tdelay(results: SimResult) -> float:
    """Extract the `tdelay` measurement from `results`."""
    # results = sim.run(opts)
    # results = sim.run(sim_options)

    if not isinstance(results, SimResult):
        raise TypeError
    print(results.an[0].measurements)
    # And return the delay value
    return results.an[0].measurements["tdelay"]


def unwrap(delays: Sequence[float]) -> np.ndarray:
    """A small bit of "data munging", to remove periodic wraps modulo the reference period."""
    delays = np.array(delays) % 2e-9  # FIXME: testbench period here
    amin = np.argmin(delays)
    delays = np.concatenate((delays[amin:], delays[:amin]))
    return delays


def save_plot(delays: Sequence[float], label: str, fname: str = "scratch/delays.png"):
    """Save a plot of the delays.
    Includes a small bit of "data munging", to remove periodic wraps modulo the reference period."""

    delays = unwrap(delays)
    print(delays)

    # And save a plot of the results
    fig, ax = plt.subplots()
    ax.set_title(label)
    ax.plot(delays * 1e12)
    ax.set_ylabel("Delay (ps)")
    ax.set_xlabel("PI Code")
    fig.savefig(fname)
