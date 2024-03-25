import amaranth as am

class UTMIIf:
    """
    UTMI Interface description for the VLSIRLOL UTMI Phy

    Attributes
    ----------
    xcvr_select : am.Signal, in
        Selects the transciver desired to the bus (HS when low)
    term_select : am.Signal, in
        Selects the bus termination mode (HS when low)
    suspend_m : am.Signal, in
        Stops the clock on the macrocell when low
    line_state : am.Signal, out
        Represents the current state of the bus or J in HS mode
    op_mode : am.Signal(2), in
        Controlls bitstuffing and hiz states

    tx_data_in : am.Signal(8), in
        Transmit data input bus
    tx_valid : am.Signal, in
        Indicates that the SIE has data to send
    tx_ready : am.Signal, out
        Indicates that the Phy is ready to sample a byte from the bus

    rx_data_out : am.Signal(8), out
        Presents the data recieved by the Phy
    rx_valid : am.Signal, out
        Indicates that the data presented on the bus is valid
    rx_active : am.Signal, out
        Indicates that the Phy has detected a sync and is recieving data
    rx_error : am.Signal, out
        Indicates that the Phy has detected an error during reception
    """
    def __init__(self):
        # State and mode management
        self.xcvr_select = am.Signal()
        self.term_select = am.Signal()
        self.suspend_m = am.Signal()
        self.line_state = am.Signal()
        self.op_mode = am.Signal(2)

        # Transmit end signals
        self.tx_data_in = am.Signal(8)
        self.tx_valid = am.Signal()
        self.tx_ready = am.Signal()

        # Recieve end signals
        self.rx_data_out = am.Signal(8)
        self.rx_valid = am.Signal()
        self.rx_active = am.Signal()
        self.rx_error = am.Signal()
