"""
# Phase Interpolator Comparisons 
"""

from typing import Callable

import matplotlib.pyplot as plt

import hdl21 as h 
from hdl21.pdk import Corner

from .tb import TbParams, save_plot, unwrap


def run_one(fn: Callable[[], float], label: str, fname: str):
    """ Run simulation function `fn` for each code """
    delays = [fn(code) for code in range(32)]
    print(delays)
    save_plot(delays, label, fname)


def run_corners(tbgen: h.Generator, label: str, fname: str):
    """ Run `sim` on `tbgen`, across corners """
    from .tb import sim 

    fig, ax = plt.subplots()

    for corner in [Corner.TYP, Corner.FAST, Corner.SLOW]:
        params = [TbParams(corner=corner, code=code) for code in range(32)]
        delays = [sim(tb=tbgen(p), params=p) for p in params]
        delays = unwrap(delays)
        print(delays)
        ax.plot(delays * 1e12, label=str(corner))
    
    # Set up all the other data on our plot
    ax.set_title(label)
    ax.set_ylabel("Delay (ps)")
    ax.set_xlabel("PI Code")
    ax.legend()

    # And save it to file
    fig.savefig(fname)


def compare():
    """ Compare CMOS and CML Phase Interpolators """

    from .test_pi import PhaseInterpTb as CmosTb
    from .test_cmlpi import PhaseInterpTb as CmlTb

    run_corners(CmosTb, "CMOS PI", "cmospi.png")
    run_corners(CmlTb, "CML PI", "cmlpi.png")
