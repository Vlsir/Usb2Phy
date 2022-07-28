""" 
# High-Speed TX
"""

from enum import Enum, auto

# Hdl & PDK Imports
import hdl21 as h
from hdl21 import Diff
from hdl21.primitives import R
import s130
from s130 import IoMosParams

Pmos = s130.modules.nmos
PmosLvt = s130.modules.nmos_lvt
Pmos = s130.modules.pmos
PmosV5 = s130.modules.pmos_v5
NmosV5 = s130.modules.nmos_v5
Nmos = s130.modules.nmos
NmosLvt = s130.modules.nmos_lvt


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


# @h.bundle
# class TxIo:
#     """Transmit Lane IO"""

#     pads = Diff(desc="Differential Transmit Pads", role=Diff.Roles.SOURCE)
#     data = TxData(desc="Data IO from Core")
#     cfg = TxConfig(desc="Configuration IO")


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
        sdata = h.Input(width=1, desc="Serial TX Data")
        sck = Diff(desc="Serial Clock", port=True, role=Diff.Roles.SINK)
        en = h.Input()
        out = TxTriplet(port=True, role=TxTriplet.Roles.SOURCE)

        # Internal Implementation
        ## FIXME!
        ## FIXME: how much simple logic to include,
        ## e.g. the requirement that enable be exclusive with dp, dn, and shunt.

    @h.module
    class HsTx:
        """
        # High-Speed TX
        """

        # IO
        VDD18, VDD33, VSS = h.Ports(3)
        # io = TxIo(port=True) # FIXME: combined bundle

        ## Pad Interface
        pads = Diff(
            desc="Differential Transmit Pads", port=True, role=Diff.Roles.SOURCE
        )
        ## Core Interface
        sdata = h.Input(width=1, desc="Serial TX Data")
        shunt = h.Input(width=1, desc="Shunt Drive Current")
        en = h.Input(width=1, desc="Enable")
        ## PLL Interface
        sck = Diff(desc="Serial Clock", port=True, role=Diff.Roles.SINK)
        ## Bias Inputs
        pbias, nbias = h.Inputs(2)

        # Internal Implementation
        ## Enable Level Shifter
        en_3v3 = h.Diff()
        ls_en = LevelShifter(inp=en, out=en_3v3, VDD18=VDD18, VDD33=VDD33, VSS=VSS)

        ## Transmit Logic & Retiming
        predriver_dp, predriver_dn, predriver_shunt = h.Signals(3)
        _predriver_inp = h.AnonymousBundle(
            # FIXME: this concatenating BundleRefs gonna work any minute now!!
            dp=predriver_dp,
            dn=predriver_dn,
            shunt=predriver_shunt,
        )
        logic = HsTxLogic(
            sdata=sdata,
            sck=sck,
            en=en,
            out=_predriver_inp,
            VDD18=VDD18,
            VSS=VSS,
        )

        ## Pre-Drivers
        driver_dp, driver_dn, driver_shunt = h.Signals(3)
        predrivers = 3 * CmosPreDriver()(
            en_3v3=en_3v3.p,
            datab_1v8=h.Concat(predriver_dp, predriver_dn, predriver_shunt),
            out=h.Concat(driver_dp, driver_dn, driver_shunt),
            VDD18=VDD18,
            VDD33=VDD33,
            VSS=VSS,
        )

        ## Output Driver
        _driver_inp = h.AnonymousBundle(
            # FIXME: this concatenating BundleRefs gonna work any minute now!!
            dp=driver_dp,
            dn=driver_dn,
            shunt=driver_shunt,
        )
        driver = HsTxDriver()(
            inp=_driver_inp,
            pads=pads,
            pbias=pbias,
            VDD18=VDD18,
            VDD33=VDD33,
            VSS=VSS,
        )

    return HsTx
