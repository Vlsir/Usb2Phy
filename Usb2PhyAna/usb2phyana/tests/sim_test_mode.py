import io
from enum import Enum
from typing import Optional

import hdl21 as h

# Set the default PDK to `s130`, in case others are in memory
import s130

h.pdk.set_default(s130.pdk)


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


class SimTest:
    # The testbench generator function
    # Must be set in sub-classes
    tbgen: Optional[h.Generator] = None

    def default_module(self) -> h.Module:
        """Generate the default-parameterized testbench module."""
        m = self.tbgen(self.default_params())
        h.pdk.compile(m)
        return m

    def default_params(self) -> "self.tbgen.Params":
        """The default parameters for our testbench generator.
        If not overridden by a subclass, attempts to zero-argument construct the generator's `Params` type.
        Note this return-type signature is pseudo-code, but should convey the idea."""

        return self.tbgen.Params()

    def netlist(self) -> None:
        """# Netlist
        Run the `SimTestMode.NETLIST` test mode.
        Default case writes a netlist for our default-parameterized generator."""
        return h.netlist(self.default_module(), dest=io.StringIO())

    def test(self, simtestmode: SimTestMode) -> None:
        """Pytest's primary entry point for classes with `Test` prefixed-names.
        Runs our test in `simtestmode`."""

        if simtestmode == SimTestMode.NETLIST:
            return self.netlist()
        if simtestmode == SimTestMode.MIN:
            return self.min()
        if simtestmode == SimTestMode.TYP:
            return self.typ()
        if simtestmode == SimTestMode.MAX:
            return self.max()
        raise ValueError(f"Invalid SimTestMode {simtestmode}")

    def min(self) -> None:
        """Test in the "MIN" SimTestMode."""
        # Default case "up-levels" to the "TYP" mode.
        return self.typ()

    def typ(self) -> None:
        """Test in the "TYP" SimTestMode."""
        # Default case "up-levels" to the "MAX" mode.
        return self.max()

    def max(self) -> None:
        """Test in the "MAX" SimTestMode."""
        raise NotImplementedError
