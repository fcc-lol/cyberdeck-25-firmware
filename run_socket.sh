#!/bin/bash
# Run the socket-enabled firmware monitor with virtual environment

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running setup..."
    bash setup.sh
fi

# Run socket firmware with sudo using the venv python
echo "Starting socket-enabled firmware monitor..."
echo "Socket server will run on http://localhost:3001"
echo ""
sudo venv/bin/python3 socket_server.py
