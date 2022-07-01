"""
HV Front-End
"""
import sys
from decimal import Decimal as D

import sitepdks as _
import s130
import hdl21 as h
from hdl21.primitives import MosParams, PhysicalResistorParams

from . import AdjustableRes, AdjustableResParams


def test_adjustable_res():
    """ Adjustable Resistor Tests """
    params = AdjustableResParams(
        mos_params=MosParams(w=D(123), l=D(100)),
        res_params=PhysicalResistorParams(w=D(100), l=D(100), model="rpoly_hp"),
        nmos=False,
        num_units=10)
    h.netlist(s130.s130.compile(h.to_proto(AdjustableRes(params))), dest=sys.stdout)

