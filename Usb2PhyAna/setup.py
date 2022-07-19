"""
# Setup Script

Derived from the setuptools sample project at
https://github.com/pypa/sampleproject/blob/main/setup.py

"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / "readme.md").read_text(encoding="utf-8")

_VLSIR_VERSION = "2.0.dev0"

setup(
    name="usb2phyana",
    version=_VLSIR_VERSION,
    description="Usb 2 Phy Custom / Analog",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Vlsir/Usb2Phy",
    author="Dan Fritchman",
    author_email="dan@fritch.mn",
    packages=find_packages(),
    python_requires=">=3.8, <4",
    install_requires=[
        f"vlsir=={_VLSIR_VERSION}",
        f"vlsirtools=={_VLSIR_VERSION}",
        f"hdl21=={_VLSIR_VERSION}",
        "pydantic==1.9.1",
    ],
    tests_require=["pytest==7.1", "numpy", "matplotlib"], # FIXME: what `pip` incantation actually gets these installed? 
    extras_require={
        "dev": ["pytest==7.1", "coverage", "pytest-cov", "black==19.10b0", "twine", "numpy", "matplotlib"]
    },
)
