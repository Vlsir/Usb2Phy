#!/bin/bash

iverilog ../../tb/tx/tb_nrzi_encoder.v \
	../../src/tx/nrzi_encoder.v \

vvp a.out

