// Module TX Statemachine
//
// Implements the state machine logic for the transmitter


module tx_state_machine(
	input clk,
	input rst_b,
	
	// TX to UTMI Interface
	input tx_valid,
	input [7:0] tx_data,
	output tx_ready,
	input fs_mode,

	// To Bit Stuffer
	output shift_reg_out,
	output shift_reg_out_valid,
	input bit_stuffed,
	input bit_stuff_ready,
	output reg packet_end
);

// Statemachine states
localparam STATE_TX_WAIT = 3'b000;
localparam STATE_SYNC_0 = 3'b001;
localparam STATE_SYNC_1 = 3'b010;
localparam STATE_TX_LOAD = 3'b011;
localparam STATE_TX_HOLD = 3'b100;
localparam STATE_EOP = 3'b101;

reg [2:0] state;

always @(posedge clk or negedge rst_b) begin
	if (!rst_b) begin
		pass;
	end else begin
		case (state) begin

		STATE_TX_WAIT: begin
			if (tx_valid) begin
				if (hs_mode) 
					state <= STATE_TX_SYNC_0;
				else 
					state <= STATE_TX_SYNC_1;
			end
		end

		STATE_SYNC_0: begin
			state <= STATE_TX_LOAD;
		end 

		STATE_SYNC_1: begin
			state <= STATE_SYNC_0;
		end

		STATE_TX_LOAD: begin
			if (tx_valid && bit_stuff_ready) begin
				state <= STATE_TX_LOAD;
			end else if (!bit_stuff_ready) begin
				state <= STATE_TX_WAIT;


		STATE_TX_DATA: begin
			if (tx_valid) begin
