import hdl21 as h
from .phyroles import PhyRoles


@h.bundle
class PhySupplies:
    """
    # PHY Supply & Ground Signals
    """

    Roles = PhyRoles  # Set the shared PHY Roles
    VDD18, VDD33, VSS = h.Signals(3, dest=Roles.PHY)
