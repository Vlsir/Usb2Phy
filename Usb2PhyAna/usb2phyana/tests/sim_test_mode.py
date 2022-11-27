import io
from enum import Enum
from dataclasses import dataclass

import hdl21 as h


class SimTestMode(Enum):
    """
    # Simulation Test Mode

    More verbosely, "how much detail do we want to test".
    Many of our simulation-based tests have long runtimes,
    which are appropriate for circuit characterization,
    but less so for, e.g. testing whether a formatting change broke their code.
    """

    NETLIST = "netlist"  # Netlist only, do not invoke simulation
    MIN = "min"  # Run the "minimum viable sim", often one setting at one corner
    TYP = "typ"  # Run a "typical amount", often one corner with many settings
    MAX = "max"  # Run everything


@dataclass
class SimTest:
    tbgen: h.Generator  # The testbench generator function

    def default(self) -> h.Module:
        return self.tbgen(self.default_params())

    def default_params(self) -> "self.tbgen.Params":
        """The default parameters for our testbench generator.
        If not overridden by a subclass, attempts to zero-argument construct the generator's `Params` type.
        Note this return-type signature is pseudo-code, but should convey the idea."""

        return self.tbgen.Params()

    def netlist(self) -> None:
        """Write a netlist for our default-parameterized"""
        return h.netlist(self.default(), dest=io.StringIO())

    def run_mode(self, simtestmode: SimTestMode) -> None:
        ...
