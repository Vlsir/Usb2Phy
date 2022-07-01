from pathlib import Path

import hdl21 as h
from hdl21.primitives import Vdc
import sitepdks as _
import s130
from vlsirtools.spice import SimOptions, SupportedSimulators, ResultFormat

from usb2phyana.hvfe.adjustable_res import AdjustableRes, AdjustableResParams


sim_options = SimOptions(
    rundir=Path("../scratch"),
    fmt=ResultFormat.SIM_DATA,
    simulator=SupportedSimulators.SPECTRE,
)


def measure_resistor(res_w: int, res_l: int, res_model: str ="rpoly_hp"):
    """ Measure the base resistor size """
    tb = h.sim.tb("ResistanceMeasurementTb")
    tb.VDD = h.Signal()
    tb.VDD_src = Vdc(Vdc.Params(dc="vddval"))(p=tb.VDD, n=tb.VSS)
    tb.dut = h.PhysicalResistor(h.PhysicalResistorParams(
        w=res_w, l=res_l, model=res_model))(p=tb.VDD, n=tb.VSS, b=tb.VSS)

    tb_compiled = h.from_proto(s130.s130.compile(h.to_proto(tb)))
    sim = h.sim.Sim(
        tb=tb_compiled.hdl21.sim.data.ResistanceMeasurementTb,
        attrs=s130.install.include(h.pdk.Corner.TYP))
    sim.dc(var="vddval", sweep=h.sim.PointSweep([1.7,1.8,1.9]))
    results = sim.run(sim_options)

    print(results)
    breakpoint()


if __name__ == '__main__':
    measure_resistor(1000, 1000)

