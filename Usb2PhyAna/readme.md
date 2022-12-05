# USB 2 PHY Analog

The [Hdl21](https://github.com/dan-fritchman/Hdl21)-based custom/ analog portions of the USB 2 PHY.  
Top-level module `Usb2PhyAna` and its IO are the sole public-intended entities.

The [usb2phyana](./usb2phyana/) package contains the design, testbenches, and simulation stimulus
for `Usb2PhyAna` and its constituent sub-blocks.

The [serdes_generics](./serdes_generics/) package includes many serdes components _not_ used in
the PHY design, but useful for many other SERDES-adjacent needs.
Many of these were designed in trial for use within the PHY,
and later abandoned for other architectural choices.

## Installation

```bash
pip install -e ".[dev]"
```

## Running Tests

The PHY package uses PyTest for unit testing, and layers several custom options to manage 
what can otherwise be long simulation times. 

Example usage:

```bash
pytest -n auto --simtestmode netlist usb2phyana
```

The custom `simtestmode` option selects one of the levels defined [here](usb2phyana/tests/sim_test_mode.py): 

```python
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
```

The `-n auto` option uses the pytest-xdist plugin to run tests in parallel. 
It is highly recommended. 

---

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
