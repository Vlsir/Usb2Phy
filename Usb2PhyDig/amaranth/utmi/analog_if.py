import amaranth as am

class AnalogIf:
    """
    Interface to the analog side of the VLSIRLOL UTMI Phy


    Questions
    ---------
        - Should we have seperate SerDes interfaces to the FS and HS drivers?
        - Should the hiz controls be FS specific?
        - Should we have a direct drive mode for HS?
        - Should we have some double-K analog detection for HS mode to check SYNC?
        - Should we have a seperate shift register or the + and - driver in HS, FS?
        - We probably want to be able to seperatly break out the recovered RX
          clock and data bypassing the elasticity buffer


    Attributes
    ----------

    upstream_pd : am.Signal, out
        Attach 15k pulldown to both data lines when asserted
    dp_pu : am.Signal, out
        Attach 1.5k pullup to the d+ line when asserted (FS)
    hs_term : am.Signal, out
        Enable the 45 Ohm HS mode termination resistors

    dp_hiz : am.Signal, out
        Place the d+ driver into the hiz state when asserted
        NOTE: This is required for soft disconnect but it's assertion
        should not affect the termination and pullup/down settings of
        a line
    dm_hiz : am.Signal, out
        Place the d- driver into the hiz state when asserted
        NOTE: This is required for soft disconnect but it's assertion
        should not affect the termination and pullup/down settings of
        a line

    dp_state : am.Signal, in
        Combinatorical state of the d+ line
    dm_state : am.Signal, in
        Combinatorical state of the d- line
    dp_fsdirect_en : am.Signal, out
        Enable direct combinatorical drive of the d+ line
        through FS driver (Optional)
    dm_fsdirect_en : am.Signal, out
        Enable direct combinatorical drive of the d- line
        through FS driver (Optional)
    dp_fsdirect : am.Signal, out
        Directly drive the d+ line FS driver (Optional)
    dm_fsdirect : am.Signal, out
        Directly drive the d- line fs driver (Optional)

    xcvr_select : am.Signal, out
        Inform the analog part of the Phy of the current mode (HS when low)

    xcvr_digireset : am.Signal, out
        Clear elasticity buffer and serdes (Optional?)

    rx_data : am.Signal(8), in
        Input data (not necessarily aligned)
        NOTE: Bits that represent idle states may be included here IFF they
        are set to one otherwise the decode has a 50% chance of failing
    rx_data_fs_eopmask : am.Signal(8), in
        Mask that represensts the bits that are actually FS SE0 states
    rx_data_valid : am.Signal, in
        First asserted when the bus leaves the idle state and the first part
        of the sync pattern is clocked in when in HS mode, in FS mode strobed
        each time a new 8 bits has been clocked in?
    rx_idle : am.Signal, in
        Should be deasserted only when the SOP has been recieved and asserted
        at reset and after rx_search_sync has been asserted
    rx_search_sync : am.Signal, out
        Indicate to the rx Phy that the bus should now be in the idle state
        and it can begin looking for a sync pattern again (Optional?)

    tx_data : am.Signal(8), out
        Output data (hopefully aligned)
    tx_data_fs_eopmask : am.Signal(8), out
        Mask that represents bits that should be FS SE0 states
    tx_data_valid : am.Signal(8), out
        Should be asserted from sync to EOP in HS mode, and strobed properly
        in FS mode maybe?
    """

    def __init__(self):
        # Termination/Pullup Settings
        self.upstream_pd = am.Signal()
        self.dp_pu = am.Signal()
        self.hs_term = am.Signal()

        # Required for soft disconnect
        self.dp_hiz = am.Signal()
        self.dm_hiz = am.Signal()

        # Combinatorical state of the lines for UTMI LineState signal
        self.dp_state = am.Signal()
        self.dm_state = am.Signal()
        
        # Direct drive for softcore FS phy implementation/debug
        self.dp_fsdirect_en = am.Signal()
        self.dm_fsdirect_en = am.Signal()
        self.dp_fsdirect = am.Signal()
        self.dm_fsdirect = am.Signal()

        # Set the SerDes gearing mode
        self.xcvr_select = am.Signal(2)

        # Empty the elasticity buffer and SerDes buffers
        self.xcvr_digireset = am.Signal()
        
        # RX SerDes interface
        self.rx_data = am.Signal(8)
        self.rx_data_fs_eopmask = am.Signal(8)
        self.rx_data_valid = am.Signal()

        # TX SerDes interface
        self.tx_data = am.Signal(8)
        self.tx_data_fs_eopmask = am.Signal(8)
        self.tx_data_valid = am.Signal()
