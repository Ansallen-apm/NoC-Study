#!/bin/bash

# Check for iverilog
if ! command -v iverilog &> /dev/null
then
    echo "Error: iverilog (Icarus Verilog) could not be found."
    echo "Please install it to run the simulation."
    exit 1
fi

# Compile
echo "Compiling RTL..."
iverilog -o noc_rtl_sim noc_top.v router.v arbiter.v

# Run
if [ -f noc_rtl_sim ]; then
    echo "Running Simulation..."
    vvp noc_rtl_sim
else
    echo "Compilation failed."
fi
