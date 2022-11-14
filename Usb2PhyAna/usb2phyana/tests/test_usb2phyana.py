""" 
# USB 2.0 Phy Custom / Analog Tests 
"""

import sys, io
import hdl21 as h
from .. import Usb2PhyAna
from .sim_test_mode import SimTestMode


def test_netlisting(simtestmode: SimTestMode):
    """Test netlisting some big-picture Modules"""

    h.netlist(Usb2PhyAna(), dest=io.StringIO(), fmt="spectre")
