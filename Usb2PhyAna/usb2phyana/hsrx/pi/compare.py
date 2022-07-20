"""
# Phase Interpolator Comparisons 
"""

import copy
import matplotlib.pyplot as plt

import hdl21 as h
from hdl21.pdk import Corner
from hdl21.prefix import m

from .tb import TbParams, save_plot, unwrap, sim_input, tdelay
from ...tests.sim_options import sim_options


def run_corners(tbgen: h.Generator, label: str, fname: str):
    """Run `sim` on `tbgen`, across corners"""

    opts = copy.copy(sim_options)
    opts.rundir = None

    fig, ax = plt.subplots()

    # PVT Conditions
    conditions = [
        {
            "corner": corner,
            "temper": temper,
            "VDD": VDD,
        }
        for corner in [Corner.TYP, Corner.FAST, Corner.SLOW]
        for temper in [-25, 25, 75]
        for VDD in [1620 * m, 1800 * m, 1980 * m]
    ]

    # Run conditions one at a time, parallelizing across PI codes
    for cond in conditions:
        # Create a list of per-code tb parameters
        pvt = TbParams(**cond)
        params = [TbParams(code=code, **cond) for code in range(32)]

        # Create the simulation inputs
        sims = [sim_input(tb=tbgen(p), params=p) for p in params]

        # Run sims
        results = h.sim.run(sims, opts)

        # Post-process the results into (code, delay) curves
        delays = [tdelay(r) for r in results]
        delays = unwrap(delays)

        # And plot the results
        label = f"{pvt.corner} {pvt.VDD} {pvt.temper}"
        ax.plot(delays * 1e12, label=label)

    # Set up all the other data on our plot
    ax.set_title(label)
    ax.set_ylabel("Delay (ps)")
    ax.set_xlabel("PI Code")
    ax.legend()

    # And save it to file
    fig.savefig(fname)


def compare():
    """Compare CMOS and CML Phase Interpolators"""

    from .test_pi import PhaseInterpTb as CmosTb
    from .test_cmlpi import PhaseInterpTb as CmlTb

    run_corners(CmosTb, "CMOS PI", "cmospi.png")
    run_corners(CmlTb, "CML PI", "cmlpi.png")
