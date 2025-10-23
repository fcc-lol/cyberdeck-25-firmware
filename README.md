# Firmware Monitor for Raspberry Pi

Monitor and control GPIO inputs including switches, buttons, and rotary encoders.

## Hardware Setup

- **Button**: GPIO 2 (Physical Pin 3)
- **Switches**: GPIO 18, 20, 21
- **Rotary Encoders**:
  - Encoder 1: A=GPIO4, B=GPIO17, Button=GPIO19
  - Encoder 2: A=GPIO27, B=GPIO22, Button=GPIO13
  - Encoder 3: A=GPIO5, B=GPIO6, Button=GPIO26
  - Encoder 4: A=GPIO23, B=GPIO24, No Button

## Quick Start

### 1. Setup (First Time Only)

```bash
cd ~/Desktop/firmware
./setup.sh
```

This will create a virtual environment and install all dependencies.

### 2. Run the Firmware

**Basic Monitor (Terminal Only):**
```bash
./run.sh
```

**Socket-Enabled Monitor (Socket Server + Events):**
```bash
./run_socket.sh
```

This starts a Socket.IO server on port 5000 that emits events on every input change.

## Files

- `firmware.py` - Basic firmware monitor (terminal display)
- `firmware_socket.py` - Socket server that emits events on input changes
- `requirements.txt` - Python dependencies
- `setup.sh` - Setup script for virtual environment
- `run.sh` - Run basic firmware
- `run_socket.sh` - Run socket server

## Socket Events

When using `firmware_socket.py`, the following events are emitted:

- `button_change` - Button state changed
- `switch_change` - Switch state changed
- `encoder_change` - Encoder value changed
- `encoder_button_press` - Encoder button pressed
- `initial_state` - Initial state on client connect

Each event includes pin/encoder info, state/value, and timestamp.

## Manual Usage

If you prefer to activate the virtual environment manually:

```bash
source venv/bin/activate
sudo venv/bin/python3 firmware.py
# or
sudo venv/bin/python3 firmware_socket.py
```

## Notes

- Scripts must run with `sudo` for GPIO access
- Press Ctrl+C to stop the monitor
- The socket server runs on port 5000 and accepts Socket.IO connections
- Build your own web interface or client to connect to the socket server
