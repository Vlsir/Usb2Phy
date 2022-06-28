"""
# Phase Interpolator Encoder 

For PIs with the combination of: 
* Two "MSB muxes", one each between I and Q phases and their complements, and 
* Thermometer-encoded LSBs 

The combination requires a saw-tooth pattern on the LSB control signals, 
which ramps up I and ramps down Q while Q leads, and ramps up Q and ramps down I while I leads. 

Note this scheme also presumes *some* phase-contributing element is "always on", 
to make MSB-mux switches have a non-zero contribution. 
The LSB output thermometer codes from this encoder generally *do not* change during 
MSB-mux switches, and the value designed to be attached to a switching MSB mux should, 
in all cases, equal zero. 

"""

# Hdl & PDK Imports
import hdl21 as h

# Local Imports
from ...width import Width
from ...logiccells import Inv, And2, And3, Or2, Buf, Xor2
from ...quadclock import QuadClock
from ...encoders import OneHotEncoder, ThermoEncoder3to8
from ...triinv import TriInv


@h.generator
def PiEncoder(p: Width) -> h.Module:
    """ Phase Interpolator Encoder """

    if p.width != 5:
        raise RuntimeError(f"yeah we know it's a parameter, but not really yet")

    @h.module
    class PiEncoder:
        # IO Interface
        VDD, VSS = h.Ports(2)
        en = h.Input(width=1, desc="Enable input")
        bin = h.Input(width=p.width, desc="Binary encoded input")

        imuxsel = h.Output(desc="In-phase mux select")
        qmuxsel = h.Output(desc="Quad-phase mux select")
        qtherm, itherm = h.Outputs(2, width=8, desc="Thermometer encoded LSB outputs")

        # Internal Implementation

        ## MSB "Encoder"
        ### Really just a buffer and XOR
        b0 = Buf(i=bin[-1], z=qmuxsel, VDD=VDD, VSS=VSS)
        x0 = Xor2(a=bin[-1], b=bin[-2], z=imuxsel, VDD=VDD, VSS=VSS)

        ## Controls for sawtooth ramping: invert LSBs when Q leads
        therm_in = h.Signal(width=3, desc="Thermometer input")
        xors = 3 * Xor2(a=bin[-2], b=bin[:-2], z=therm_in, VDD=VDD, VSS=VSS)

        ## Thermometer LSB Encoder
        encoder = ThermoEncoder3to8(bin=therm_in, out=qtherm, en=en, VDD=VDD, VSS=VSS)
        therm_invs = 8 * Inv(i=qtherm, z=itherm, VDD=VDD, VSS=VSS)

    return PiEncoder
