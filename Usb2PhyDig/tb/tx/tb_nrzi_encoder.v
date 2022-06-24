// Testbench for the serial domain NRZI Encoder


`timescale 1ps/1ps

`define assert(signal, value) \
	if (signal != value) begin \
		$display("ASSERTION FAILED in %m: signal != value"); \
	end


module tb_nrzi_encoder();


localparam CLKPERIOD = 208; // 480MHz

reg clk;
reg rst_b;
reg din;
reg din_valid;

wire dout;


nrzi_encoder DUT (
	.clk(clk),
	.rst_b(rst_b),
	.din(din),
	.din_valid(din_valid),
	.dout(dout)
);


initial begin
	clk = 1'b0;
	forever #(CLKPERIOD / 2) clk = ~clk;
end


task test_nrzi_hs(); 
	begin
		rst_b = 1'b0;
		#(4 * CLKPERIOD);
		rst_b = 1'b1;
		`assert(dout, 1'b1); // USB Line idle state should be 1
		
		din = 1'b0;
		din_valid = 1'b1;
		#(CLKPERIOD);
		`assert(dout, 1'b0); // 0's cause transition
		
		din = 1'b1;
		#(CLKPERIOD);
		`assert(dout, 1'b0); // Should stay at 0
		
		din = 1'b0;
		#(CLKPERIOD);
		`assert(dout, 1'b1); // Transition to 1
		
		din = 1'b1;
		#(CLKPERIOD);
		`assert(dout, 1'b1); // Stay at 1
		
		din = 1'b0;
		din_valid = 1'b0;
		#(CLKPERIOD);
		`assert(dout, 1'b1); // Stay at 1, valid not asserted
		#(CLKPERIOD);
		`assert(dout, 1'b1); // Stay at 1, valid not asserted
	       	
		rst_b = 1'b0;
	end
endtask


initial begin
	$dumpfile("test.vcd");
	$dumpvars;
	test_nrzi_hs();
	$finish;
end

endmodule 
