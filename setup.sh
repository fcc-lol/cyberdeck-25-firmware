#!/bin/bash
# Setup script for firmware virtual environment

echo "Setting up firmware virtual environment..."
echo "=========================================="

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo ""
echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo ""
echo "To run the firmware:"
echo "  ./run.sh                 (basic firmware monitor)"
echo "  ./run_socket.sh          (socket-enabled version)"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  sudo venv/bin/python3 firmware.py"
