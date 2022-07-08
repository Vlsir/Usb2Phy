""" 
# USB 2.0 Phy Custom / Analog Tests 
"""

# PyPi Imports
import numpy as np
import matplotlib.pyplot as plt 

# HDL & PDK Imports
import sitepdks as _
import s130
from s130 import MosParams, IoMosParams
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.sim import Sim, LogSweep
from hdl21.prefix import e

nmos = s130.modules.nmos
nmos_lvt = s130.modules.nmos_lvt
pmos = s130.modules.pmos
pmos_hvt = s130.modules.pmos_hvt
pmos_v5 = s130.modules.pmos_v5

# DUT Imports
from .sim_options import sim_options


def test_netlisting():
    """ Test netlisting some big-picture Modules """
    import sys
    from .. import Usb2PhyAna

    h.netlist(h.to_proto(Usb2PhyAna), dest=sys.stdout)

