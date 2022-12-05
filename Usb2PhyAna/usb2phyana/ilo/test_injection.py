""" 
# ILO Tests 
"""

import pickle, io
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
from ..tests.sim_test_mode import SimTestMode


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
        width=5 * PICO,
        delay=4 * n,
    )(p=tb.inj, n=tb.VSS)

    return tb


def test_ilo_injection(simtestmode: SimTestMode):
    """Ilo Injection Test(s)"""
    if simtestmode in (SimTestMode.MIN, SimTestMode.NETLIST):
        # In min-mode just netlist
        params = TbParams(pvt=Pvt(), ilo=IloParams(), code=1)
        h.netlist(IloInjectionTb(params), dest=io.StringIO())
    else:
        # And in any other mode run simulation
        sim_ilo_injection()


def sim_ilo_injection():
    # Get the best DAC code from saved frequency-sweep results
    pvt = Pvt()
    dac_code_result = Result(**pickle.load(open(dac_code_result_pickle_file, "rb")))
    dac_code = best_dac_code(result=dac_code_result, pvt=pvt)

    params = TbParams(pvt=pvt, ilo=IloParams(), code=dac_code)

    # Create some simulation stimulus
    @hs.sim
    class IloSim:
        # The testbench
        tb = IloInjectionTb(params)

        # Our sole analysis: transient, for much longer than we need.
        # But auto-stopping when measurements complete.
        tr = hs.Tran(tstop=250 * n)

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

    results = IloSim.run(sim_options)
    print(results)
