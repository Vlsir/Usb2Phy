// Bit Stuffing Module
// Input follows a Ready-Valid interface
// Output is valid only, no ready handshaking
// The clock frequency for this module is assumed to be
// 480MHz
// For HS data, it is assumed valid will be asserted 
// throughout the packet
// The stuffed output is raised any time a bit is stuffed
// THe input packet_end signifies the end of a packet

module bit_stuffer(
	input clk,
	input rst_b,
	input din,
	input din_valid,
	output din_ready,
	input packet_end,
	
	output reg dout,
	output reg dout_valid,
	output reg stuffed
);

reg [2:0] ones_count;

always @(posedge clk or negedge rst_b) begin
	if (!rst_b) begin 
		ones_count <= 3'b0;
		dout <= 1'b0;
		dout_valid <= 1'b0;
		stuffed <= 1'b0;
	end else begin
		if (din_valid && din_ready) begin
			if (din) begin
				if (ones_count > 3'd6) begin
					dout <= 1'b0;
					din_ready <= 1'b0;
					stuffed <= 1'b1;
					ones_count <= 3'd0;
				end else begin
					dout <= din;
					din_ready <= 1'b1;
					stuffed <= 1'b0;
					ones_count <= ones_counter + 3'd1;
				end
			end else begin
				dout <= din;
				din_ready <= 1'b1;
				ones_count <= ones_count;
				stuffed <= 1'b0;
			end
			
			dout_valid <= 1'b1;
		end else if (!din_ready) begin
			// Previous bit was stuffed
			dout <= 1'b1;
			din_ready <= 1'b0;
			stuffed <= 1'b0;
			ones_count <= ones_count;
			dout_valid <= 1'b1;
		end else begin
			// Waiting for input
			dout <= 1'b0;
			din_ready <= 1'b1;
			stuffed <= 1'b0;
			dout_valid <= 1'b0;
			if (packet_end)
				ones_counter <= 3'd0;
			else
				ones_count <= ones_count + 1;
		end
	end
end

endmodule 
