# Cyberdeck 25 Firmware

Firmware for the Cyberdeck 25 - a Raspberry Pi-based portable computer with custom hardware inputs. This firmware monitors all physical inputs (switches, buttons, and rotary encoders) and broadcasts their state in real-time via a Socket.IO server, allowing web interfaces and other clients to respond to user input events.

## What It Does

The Cyberdeck 25 firmware runs a lightweight Python socket server that:
- Monitors all GPIO inputs with sub-millisecond polling for responsive encoder tracking
- Broadcasts input changes to connected clients via WebSocket (Socket.IO)
- Provides real-time state updates for building responsive UIs
- Handles debouncing and quadrature decoding for rotary encoders
- Emits structured events with timestamps for every input change

This allows you to build web-based interfaces, control panels, or automation systems that respond instantly to physical inputs on the Cyberdeck 25.

## Hardware Inputs

The Cyberdeck 25 features:

- **1 Key Button**: GPIO 2 (Physical Pin 3) - Primary action button
- **3 Toggle Switches**: GPIO 18 (Green), GPIO 20 (Blue), GPIO 21 (Red)
- **4 Rotary Encoders** with push buttons:
  - Encoder 1: A=GPIO5, B=GPIO6, Button=GPIO26
  - Encoder 2: A=GPIO27, B=GPIO22, Button=GPIO13
  - Encoder 3: A=GPIO4, B=GPIO17, Button=GPIO19
  - Encoder 4: A=GPIO23, B=GPIO24 (no button)

All inputs use pull-up resistors and are active-low (pressed/switched = LOW, released = HIGH).

## Quick Start

### 1. Initial Setup

```bash
./setup.sh
```

Creates a Python virtual environment and installs all required dependencies (Flask, Flask-SocketIO, RPi.GPIO).

### 2. Run the Socket Server

```bash
./run_socket.sh
```

Starts the firmware socket server on `http://0.0.0.0:5000` (accessible from any device on the network).

### 3. Connect Your Client

Connect to the Socket.IO server from any web app, Python script, or Socket.IO client to receive real-time input events.

## Socket Events

The server emits the following events to all connected clients:

### `key_change`
Emitted when the main button state changes.
```json
{
  "active": true,
  "timestamp": 1729713845.123
}
```

### `switch_change`
Emitted when any toggle switch changes position.
```json
{
  "switch": "green",
  "active": false,
  "timestamp": 1729713845.456
}
```

### `encoder_change`
Emitted when any encoder is rotated.
```json
{
  "encoder_id": 1,
  "value": 15,
  "direction": "right",
  "timestamp": 1729713845.789
}
```

### `encoder_button_press`
Emitted when an encoder button is pressed (also resets encoder counter to 0).
```json
{
  "encoder_id": 2,
  "timestamp": 1729713846.012
}
```

### `initial_state`
Sent to newly connected clients with current state of all inputs.
```json
{
  "key": {"active": true},
  "switches": {
    "green": {"active": true},
    "blue": {"active": false},
    "red": {"active": true}
  },
  "encoders": {
    "1": 5,
    "2": -3,
    "3": 0,
    "4": 12
  },
  "timestamp": 1729713846.234
}
```

## Files

- `socket_server.py` - Main firmware socket server
- `inputs_debug.py` - Debug script for testing inputs
- `requirements.txt` - Python dependencies
- `setup.sh` - One-time setup script
- `run_socket.sh` - Launcher script for socket server

## Architecture

The firmware uses:
- **Flask + Flask-SocketIO** for WebSocket communication
- **RPi.GPIO** for hardware input monitoring
- **Threaded monitoring loop** for high-frequency polling (0.1ms intervals)
- **sysfs GPIO** for switch monitoring (more reliable for toggle switches)
- **Quadrature decoding** for accurate rotary encoder tracking

The monitoring loop runs in a separate thread while Flask-SocketIO handles client connections and event broadcasting.

## Development

To manually run with the virtual environment:

```bash
source venv/bin/activate
sudo venv/bin/python3 socket_server.py
```

Note: `sudo` is required for GPIO access on Raspberry Pi.

## Network Access

The socket server binds to `0.0.0.0:5000`, making it accessible from:
- `http://localhost:5000` (on the Pi itself)
- `http://[pi-ip-address]:5000` (from other devices on the network)

CORS is enabled for all origins, allowing any web client to connect.
