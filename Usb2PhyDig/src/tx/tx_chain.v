// Module TX Chain
//
// Implements all components of the tx chain 
// This module is assumed to be clocked at 480MHz


module tx_chain(
	input clk,
	input rst_b,

	input [7:0] tx_data,
	input tx_valid,
	output tx_ready,

	output fs_data,
	output hs_data,
	input fs_mode,

	input disable_nrzi_bistuff
);
