import hdl21 as h
from usb2phyana import tetris
from usb2phyana.tetris.mos import Nmos, Pmos


def test_tetris1():

    h.elaborate(
        [
            Nmos(nser=1),
            Nmos(nser=2),
            Nmos(nser=4),
            Nmos(nser=8),
            Nmos(nser=16),
        ]
    )

    h.elaborate(
        [
            Pmos(nser=1),
            Pmos(nser=2),
            Pmos(nser=4),
            Pmos(nser=8),
            Pmos(nser=16),
        ]
    )
