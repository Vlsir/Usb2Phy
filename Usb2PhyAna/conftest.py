import pytest
from usb2phyana.tests.sim_test_mode import SimTestMode

# Create a lookup from string-value to enum variant
modes = {m.value: m for m in SimTestMode}


def pytest_addoption(parser):
    parser.addoption(
        "--simtestmode",
        action="store",
        default=SimTestMode.TYP.value,
        help="Simulation test mode. One of {[m.value for m in SimTestMode]}.",
    )


@pytest.fixture
def simtestmode(request):
    """Get the SimTestMode command-line option, and convert it to our enum."""
    parser_option = request.config.getoption("--simtestmode")
    if parser_option not in modes:
        raise RuntimeError(f"Invalid SimTestMode: {parser_option}")
    return modes[parser_option]
