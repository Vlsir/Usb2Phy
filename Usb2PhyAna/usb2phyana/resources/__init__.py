"""
# External Resources Package

Supplies non-Python files as `pathlib.Path`s. 
"""

from os import PathLike
from pathlib import Path

# The `resources` Path object.
# Can be used in path-style slash operators such as
# ```
# import resources
# myfile = resources / "myfilename"
# ```
resources = Path(__file__).parent


def resource(name: PathLike) -> Path:
    """Get the resource `name`"""
    return resources / name
