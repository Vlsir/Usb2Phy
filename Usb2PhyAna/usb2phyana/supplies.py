import hdl21 as h


@h.bundle
class PhySupplies:
    """
    # PHY Supply & Ground Signals
    """

    VDD18, VDD33, VSS = h.Signals(3)
