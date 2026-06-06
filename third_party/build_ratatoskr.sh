#!/bin/bash
cd "$(dirname "$0")/ratatoskr/simulator"
if [ ! -f "sim" ]; then
    echo "Building Ratatoskr Simulator..."
    ./build.sh
else
    echo "Ratatoskr Simulator already built."
fi
