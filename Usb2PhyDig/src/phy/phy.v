
// 
// # Usb2 Phy Digital 
// 
// Top-Level modules for PHY digital logic. 
// 
module usb2phydig (

	input resetn_n, // Active-Low Reset. 
	// FIXME: whether reset from the controller will be shared with config/ debug/ etc, or we need more than one. 

	// UTMI Interface 
	output utmi_clk, // FIXME: whether this will be separate from the analog-interface clock 
	// UTMI Controls 
	input utmi_xcvr_select, // Transceiver Select
	input utmi_term_select, // Termination Select
	input utmi_suspend_n, // Active-Low Suspend 
	output [1:0] utmi_line_state, // Received Line State
	input [1:0] utmi_opmode, // Operation Mode
	// UTMI TX 
	input [7:0] utmi_datain, // TX Data Input
	input utmi_tx_valid, // TX Valid 
	output utmi_tx_ready, // TX Ready
	// UTMI RX 
	output [7:0] utmi_dataout, // RX Data Output
	output utmi_rx_valid, // RX Valid
	output utmi_rx_active, // RX Active
	output utmi_rx_error, // RX Error

	// Analog Phy Interface 
	input phy_sclk, // Serial Clock
	input phy_rx_sdata, // RX Serial Data
	output phy_tx_sdata, // RX Serial Data
	// ... FIXME! many more. 

	// Configuration Interface 
	// FIXME: sort out just what this is - SPI, JTAG, etc.
	input debug_jtag_tck,
	input debug_jtag_tms,
	input debug_jtag_tdi,
	output debug_jtag_tdo,
	
);

	// TODO: some actual content! 

endmodule // usb2phydig 
