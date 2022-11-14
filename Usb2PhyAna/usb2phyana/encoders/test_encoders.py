""" 
# Encoders
## Unit Tests 
"""

# Std-Lib Imports
import io

# Hdl & PDK Imports
import sitepdks as _
import s130
import hdl21 as h
from hdl21.pdk import Corner
from hdl21.sim import Sim, LinearSweep, SaveMode
from hdl21.prefix import m, n, PICO
from hdl21.primitives import Vpulse, Vdc

# DUT Imports
from .. import resources
from ..tests.sim_options import sim_options
from .encoders import OneHotEncoder, ThermoEncoder3to8


@h.paramclass
class TbParams:
    width = h.Param(dtype=int, desc="Encoder (Binary) Bus Width")
    code = h.Param(dtype=int, desc="Input Code")
    VDD = h.Param(dtype=h.Prefixed, desc="Supply Voltage Value")


@h.generator
def ThermoEncoderTb(p: TbParams) -> h.Module:
    """Phase Interpolator Testbench"""

    tb = h.sim.tb("ThermoEncoderTb")

    # Generate and drive VDD
    tb.VDD = h.Signal()
    tb.vvdd = Vdc(Vdc.Params(dc=p.VDD, ac=0 * m))(p=tb.VDD, n=tb.VSS)

    # Set up the select/ code input
    tb.code = h.Signal(width=p.width)

    def vbit(i: int):
        """Create a `Vdc` call equal to either `p.VDD` or zero."""
        val = p.VDD if i else 0 * m
        return Vdc(Vdc.Params(dc=val, ac=0 * m))

    def vcode(code: int) -> None:
        """Closure to drive `tb.code` to the (binary) value of `code`.
        Essentially an integer to binary, and then binary to `Vdc.Params` converter."""

        if code < 0 or code >= 2**p.width:
            raise ValueError

        # Convert to a binary-valued string
        bits = bin(code)[2:].zfill(tb.code.width)

        # And create a voltage source for each bit
        for idx in range(p.width):
            bitval = int(bits[-(idx + 1)])
            vinst = vbit(bitval)(p=tb.code[idx], n=tb.VSS)
            tb.add(name=f"vcode{idx}", val=vinst)

    # Call all that to drive the code bus
    vcode(p.code)

    tb.therm = h.Signal(width=8)
    tb.dut = ThermoEncoder3to8(
        VDD=tb.VDD, VSS=tb.VSS, bin=tb.code, out=tb.therm, en=tb.VDD
    )
    return tb


def sim_thermo_encoder(p: TbParams) -> None:
    """Thermometer Encoder Sim"""

    print(f"Simulating ThermoEncoder for code {p.code}")

    tb = ThermoEncoderTb(p)

    # Craft our simulation stimulus
    sim = Sim(tb=tb, attrs=s130.install.include(Corner.TYP))
    sim.op()

    sim.include(
        resources / "scs130lp.sp"
    )  # FIXME! relies on this netlist of logic cells
    # sim_options.rundir = Path(f"./scratch/code{code}")
    results = sim.run(sim_options)

    # Check we got the right thermometer-encoded output
    data = results.an[0].data
    therm = [data[f"xtop.therm_{idx}"] for idx in range(2**p.width)]
    for idx in range(p.code + 1):
        assert therm[idx] > 0.99 * float(p.VDD)
    for idx in range(p.code + 1, (2**p.width) - 1):
        assert therm[idx] < 0.01 * float(p.VDD)


from ..tests.sim_test_mode import SimTestMode


def test_thermo_encoder(simtestmode: SimTestMode):
    """Thermo Encoder Test(s)"""
    if simtestmode == SimTestMode.NETLIST:
        p = TbParams(VDD=1800 * m, code=1, width=3)
        return h.netlist(ThermoEncoderTb(p), dest=io.StringIO())
    if simtestmode == SimTestMode.MIN:
        codes = [5]  # Just run one code
    else:
        codes = range(8)

    for code in codes:
        p = TbParams(VDD=1800 * m, code=code, width=3)
        sim_thermo_encoder(p)
