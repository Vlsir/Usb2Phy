from enum import Enum, auto


class PhyRoles(Enum):
    """# Enumerated Roles for PHY Bundles

    Many high-level PHY blocks share this set of roles,
    particularly for control signals which are driven by the same
    external PHY-digital block."""

    PHY = auto()  # The (analog) PHY
    EXT = auto()  # Everything external, i.e. the rest of the world
