""" 
# ILO Tests 
"""

import pickle, io, copy
from pathlib import Path
import numpy as np

# Hdl Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.prefix import m, n, PICO
from hdl21.primitives import Vpulse

# PDK Imports
import s130
import sitepdks as _

# Local/ DUT Imports
from .ilo import IloParams
from .tb import Pvt, TbParams, IloSharedTb, tperiod
from .test_dac_code import Result, result_pickle_file as dac_code_result_pickle_file
from ..tests.sim_options import sim_options
from ..tests.sim_test_mode import SimTest


def best_dac_code(result: Result, pvt: Pvt) -> int:
    """Get the best Dac code for a given PVT"""

    index = result.conditions.index(pvt)
    cond_results = result.results[index]

    # Post-process the results into (ib, period) curves
    freqs = np.array([1 / tperiod(r) for r in cond_results])

    for code in result.codes:
        print(code, freqs[code] / 1e6)

    # Numpy interpolation requires the x-axis array be NaN-free
    # This often happens at low Vdd, when the ring fails to oscillate,
    # or goes slower than we care to simulate.
    # Replace any such NaN values with zero.
    # If there are any later in the array, this interpolation will fail.
    freqs_no_nan = np.nan_to_num(freqs, copy=True, nan=0)
    code_480 = np.interp(x=480e6, xp=freqs_no_nan, fp=result.codes)
    print(code_480)
    return round(code_480)


@h.generator
def IloInjectionTb(params: TbParams) -> h.Module:
    """# Ilo Injection Testbench Generator"""

    # Create our testbench
    tb = IloSharedTb(params=params, name="IloInjectionTb")

    # Create the injection-pulse source, which also serves as our kick-start
    tb.vinj = Vpulse(
        v1=0 * m,
        v2=1800 * m,
        period=16667 * PICO,  # ~ 60MHz
        rise=10 * PICO,
        fall=10 * PICO,
        width=100 * PICO,
        delay=3000 * PICO,
    )(p=tb.inj, n=tb.VSS)

    return tb


def sim_ilo_injection():
    pvt = Pvt()

    # Get the best DAC code from saved frequency-sweep results
    # FIXME: recreate good values in this pickled data! It's gotten outta whack
    # dac_code_result = Result(**pickle.load(open(dac_code_result_pickle_file, "rb")))
    # dac_code = best_dac_code(result=dac_code_result, pvt=pvt)
    dac_code = 11

    params = TbParams(pvt=pvt, ilo=IloParams(), code=dac_code)
    tb_ = IloInjectionTb(params)
    h.pdk.compile(tb_)

    # Create some simulation stimulus
    @hs.sim
    class IloSim:
        # The testbench
        tb = tb_

        # Our sole analysis: transient, for much longer than we need.
        # But auto-stopping when measurements complete.
        tr = hs.Tran(tstop=7500 * n)

        # The stuff we can't first-class represent, and need to stick in a literal.
        l = hs.Literal(
            f"""
            simulator lang=spice
            .ic xtop.stg0_p 900m
            .ic xtop.stg0_n 0
            .temp {params.pvt.t}
            simulator lang=spectre
        """
        )

        i = hs.Include(s130.resources / "stdcells.sp")

    # Add the PDK dependencies
    IloSim.add(*s130.install.include(params.pvt.p))

    opts = copy.copy(sim_options)
    opts.rundir = Path("scratch")

    results = IloSim.run(opts)
    print(results)


class TestIloInjection(SimTest):
    """Ilo Injection Test(s)"""

    tbgen = IloInjectionTb

    def min(self):
        return self.netlist()

    def typ(self):
        return sim_ilo_injection()

    def max(self):
        # FIXME: add corner runs
        raise NotImplementedError
