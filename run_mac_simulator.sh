#!/bin/bash
# Run the cyberdeck Mac simulator

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Run simulator
echo "Starting Cyberdeck Mac Simulator..."
echo "Socket server will run on http://localhost:3001"
echo ""
venv/bin/python3 mac_simulator.py --port 3001

