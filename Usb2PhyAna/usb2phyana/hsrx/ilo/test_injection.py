""" 
# ILO Tests 
"""

import pickle
from typing import List, Tuple, Optional
from dataclasses import asdict
from copy import copy
from pathlib import Path

from pydantic.dataclasses import dataclass
import numpy as np
import matplotlib.pyplot as plt

# Hdl & PDK Imports
import hdl21 as h
import hdl21.sim as hs
from hdl21.pdk import Corner
from hdl21.sim import Sim, LogSweep
from hdl21.prefix import m, µ, f, n, T, PICO
from hdl21.primitives import Vdc, Vpulse, Idc, C
import s130
import sitepdks as _

from ...tests.sim_options import sim_options

# DUT Imports
from .ilo import IloParams
from .tb import Pvt, TbParams, IloFreqTb, IloInjectionTb, sim_input


def test_ilo_injection():
    """Ilo Injection Test(s)"""

    # Create our parametric testbench
    params = TbParams(pvt=Pvt(v=900 * m), ilo=IloParams(cl=30 * f))
    tb = IloInjectionTb(params)

    # And simulation input for it
    sim = Sim(tb=tb, attrs=s130.install.include(Corner.TYP))
    sim.tran(tstop=20 * n)

    # Run some spice
    results = sim.run(sim_options)
    print(results)
