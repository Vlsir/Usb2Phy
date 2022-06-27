// Module nrzi_encoder
// Encodes the input data stream to create an NRZI output
// The Input follows a valid only interface
// The output is held to the previous state when the input is invalid

module nrzi_encoder(
	input clk,
	input rst_b,
	input din,
	input din_valid,
	output dout
);

reg state;
assign dout = state;

always @(posedge clk or negedge rst_b) begin
	if (!rst_b) 
		state <= 1'b1;
	else begin
		if (din_valid) 
			state <= (din) ? state : ~state;
		else
			state <= state;
	end
end

endmodule
