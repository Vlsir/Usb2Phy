""" 
# High-Speed TX
"""

from enum import Enum, auto

# Hdl & PDK Imports
import hdl21 as h
from hdl21 import Diff

import s130
from s130 import IoMosParams

Pmos = s130.modules.pmos
PmosV5 = s130.modules.pmos_v5
NmosV5 = s130.modules.nmos_v5
Nmos = s130.modules.nmos
NmosLvt = s130.modules.nmos_lvt

# Local Imports
from ..supplies import PhySupplies
from ..phyroles import PhyRoles


@h.bundle
class TxTriplet:
    """Bundle of the three legs of the high-speed TX:
    DP, DN, and "Shunt to Ground"."""

    class Roles(Enum):
        # Clock roles: source or sink
        SOURCE = auto()
        SINK = auto()

    dp, dn, shunt = h.Signals(3, src=Roles.SOURCE, dest=Roles.SINK)


@h.generator
def CmosPreDriver(_: h.HasNoParams) -> h.Module:
    """
    # Cmos Pre-Driver

    Implements the three-state driver which places
    each leg of the TxDriver in one of:
    * Driving current (out = VSS)
    * Not driving current (out = VDD18)
    * Hard disabled (out = VDD33)

    This scheme injects dependencies that:
    * (a) VDD18 is *never on* when VDD33 is *not*
    * (b) Input `datab_1v8` is *never* high when Input en_3v3 is also low.

    Logic above this level must ensure the latter,
    while system-level design must ensure the former.

    With all those caveats, the circuit is really just a special NAND2 gate
    in which two of the devices are IO (5V) and the other two are core (1.8V).
    """

    m = h.Module()
    m.VDD18, m.VDD33, m.VSS = h.Ports(3)
    m.datab_1v8, m.en_3v3 = h.Inputs(2)
    m.out = h.Output()

    # This right here is the fun transistor, where the 1.8-3.3V dependency is injected!
    m.pdata = Pmos(m=60)(d=m.out, g=m.datab_1v8, s=m.VDD18, b=m.VDD33)
    m.pen = PmosV5(m=4)(d=m.out, g=m.en_3v3, s=m.VDD33, b=m.VDD33)
    m.nen = NmosV5(m=20)(d=m.out, g=m.en_3v3, b=m.VSS)
    m.data = NmosLvt(m=40)(d=m.nen.s, g=m.datab_1v8, s=m.VSS, b=m.VSS)

    return m


@h.generator
def HsTxDriver(_: h.HasNoParams) -> h.Module:
    """# High Speed Transmit Driver"""

    # Define a few reused device-parameter combos
    MIRROR_RATIO = 170  # ?!?!
    PswitchMini = PmosV5(IoMosParams(m=4))
    Pswitch = PmosV5(IoMosParams(m=4 * MIRROR_RATIO))
    Pbias = PmosV5(IoMosParams(l=1, m=10))

    m = h.Module()

    # IO
    m.VDD18, m.VDD33, m.VSS = h.Ports(3)
    m.pads = Diff(port=True, role=Diff.Roles.SOURCE, desc="Differential Output Pads")
    m.inp = TxTriplet(port=True, role=TxTriplet.Roles.SINK)
    m.pbias = h.Input(desc="100µA Pmos Bias Current")

    # Internal Implementation
    ## Current Mirror - 100 to 17,000 µA
    m.pdiode = Pbias(g=m.pbias, s=m.VDD33, b=m.VDD33)
    m.switch_diode = PswitchMini(g=m.VSS, s=m.pdiode.d, d=m.pbias, b=m.VDD33)
    m.psrc = MIRROR_RATIO * Pbias(g=m.pbias, s=m.VDD33, b=m.VDD33)

    ## Switches
    m.switch_dp = Pswitch(g=m.inp.dp, d=m.pads.p, s=m.psrc.d, b=m.VDD33)
    m.switch_dn = Pswitch(g=m.inp.dn, d=m.pads.n, s=m.psrc.d, b=m.VDD33)
    m.shunt_switch = Pswitch(g=m.inp.shunt, d=m.VSS, s=m.psrc.d, b=m.VDD33)

    return m


@h.bundle
class HsTxBias:
    """# High-Speed TX Bias Bundle"""

    Roles = PhyRoles  # Set the shared PHY Roles
    pbias, nbias = h.Inputs(2)


@h.bundle
class HsTxDig:
    """# High-Speed TX Digital IO Bundle"""

    Roles = PhyRoles  # Set the shared PHY Roles
    sck = h.Output(width=1, desc="High-Speed TX *Output* Serial TX Clock")
    sdata = h.Input(width=1, desc="High-Speed TX Data")
    shunt = h.Input(width=1, desc="High-Speed TX Shunt Drive Current")
    en = h.Input(width=1, desc="High-Speed TX Output Enable")


@h.generator
def HsTx(_: h.HasNoParams) -> h.Module:
    @h.module
    class LevelShifter:
        """Logic Level Shifter, 1.8V to 3.3V"""

        # IO
        VDD18, VDD33, VSS = h.Ports(3)
        inp = h.Input()
        out = h.Diff(port=True)

        # Internal Implementation
        ## FIXME!

    @h.module
    class HsTxLogic:
        """Tx Logic"""

        # IO
        VDD18, VSS = h.Ports(2)
        core_if = HsTxDig(port=True)
        out = TxTriplet(port=True, role=TxTriplet.Roles.SOURCE)

        # Internal Implementation
        ## FIXME: how much simple logic to include,
        ## e.g. the requirement that enable be exclusive with dp, dn, and shunt.

    @h.module
    class HsTx:
        """
        # High-Speed TX
        """

        # IO
        SUPPLIES = PhySupplies(port=True, role=PhyRoles.PHY, desc="Supplies")
        pads = Diff(port=True, role=Diff.Roles.SOURCE, desc="Transmit Pads")
        pllsck = Diff(port=True, role=Diff.Roles.SINK, desc="Tx Pll Serial Clock")
        dig = HsTxDig(port=True, role=PhyRoles.PHY, desc="Digital IO")
        bias = HsTxBias(port=True, role=PhyRoles.PHY, desc="Bias Inputs")

        # FIXME: need to add a driver for the single-ended `sck` output.

        # Implementation
        ## Enable Level Shifter
        en_3v3 = h.Diff()
        ls_en = LevelShifter(
            inp=dig.en,
            out=en_3v3,
            VDD18=SUPPLIES.VDD18,
            VDD33=SUPPLIES.VDD33,
            VSS=SUPPLIES.VSS,
        )

        ## Transmit Logic & Retiming
        predriver_dp, predriver_dn, predriver_shunt = h.Signals(3)
        _predriver_inp = h.AnonymousBundle(
            # FIXME: this concatenating BundleRefs gonna work any minute now!!
            dp=predriver_dp,
            dn=predriver_dn,
            shunt=predriver_shunt,
        )
        logic = HsTxLogic(
            core_if=dig,
            out=_predriver_inp,
            VDD18=SUPPLIES.VDD18,
            VSS=SUPPLIES.VSS,
        )

        ## Pre-Drivers
        driver_dp, driver_dn, driver_shunt = h.Signals(3)
        predrivers = 3 * CmosPreDriver()(
            en_3v3=en_3v3.p,
            datab_1v8=h.Concat(predriver_dp, predriver_dn, predriver_shunt),
            out=h.Concat(driver_dp, driver_dn, driver_shunt),
            VDD18=SUPPLIES.VDD18,
            VDD33=SUPPLIES.VDD33,
            VSS=SUPPLIES.VSS,
        )
        ## Output Driver
        _driver_inp = h.AnonymousBundle(
            # FIXME: this concatenating BundleRefs gonna work any minute now!!
            dp=driver_dp,
            dn=driver_dn,
            shunt=driver_shunt,
        )
        driver = HsTxDriver(h.Default)(
            inp=_driver_inp,
            pads=pads,
            pbias=bias.pbias,
            VDD18=SUPPLIES.VDD18,
            VDD33=SUPPLIES.VDD33,
            VSS=SUPPLIES.VSS,
        )

    return HsTx
