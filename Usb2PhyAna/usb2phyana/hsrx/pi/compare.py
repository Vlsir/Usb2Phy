"""
# Phase Interpolator Comparisons 
"""

from typing import Callable, Sequence

import numpy as np
import matplotlib.pyplot as plt


def save_plot(delays: Sequence[float], label:str, fname: str = "delays.png"):
    """ Save a plot of the delays. 
    Includes a small bit of "data munging", to remove periodic wraps modulo the reference period. """
    
    # Unwrap the period from the delays
    delays = np.array(delays) % 2e-9 # FIXME: testbench period here
    amin = np.argmin(delays)
    delays = np.concatenate((delays[amin:], delays[:amin]))
    print(delays)

    # And save a plot of the results
    fig, ax = plt.subplots()
    ax.set_title(label)
    ax.plot(delays * 1e12)
    ax.set_ylabel("Delay (ps)")
    ax.set_xlabel("PI Code")
    fig.savefig(fname)


def run_one(fn: Callable[[], float], label: str, fname: str):
    """ Run simulation function `fn` for each code """
    delays = [fn(code) for code in range(32)]
    print(delays)
    save_plot(delays, label, fname)


def compare():
    """ Compare CMOS and CML Phase Interpolators """

    from .test_pi import sim_phase_interp as cmos_sim
    from .test_cmlpi import sim_phase_interp as cml_sim

    run_one(cmos_sim, "CMOS PI", "cmospi.png")
    run_one(cml_sim, "CML PI", "cmlpi.png")
