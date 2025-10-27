#!/usr/bin/env python3
"""
CLI Mac Simulator for Cyberdeck Inputs
Simulates socket events using keyboard inputs
"""

import curses
import time
import sys
from threading import Thread, Lock
from flask import Flask
from flask_socketio import SocketIO, emit

# Flask app setup
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

class SimulatorServer:
    def __init__(self, socketio):
        self.socketio = socketio
        self.lock = Lock()
        self.connected_clients = 0
        
        # State tracking
        self.key_active = True  # Default to released (True)
        self.switches = {
            'green': True,   # Default to released (True)
            'blue': True,
            'red': True
        }
        self.encoders = {
            1: 0,
            2: 0,
            3: 0,
            4: 0
        }
    
    def emit_key_change(self, active):
        """Emit key change event"""
        self.key_active = active
        self.socketio.emit('key_change', {
            'active': active,
            'timestamp': time.time()
        })
    
    def emit_switch_change(self, color, active):
        """Emit switch change event"""
        self.switches[color] = active
        self.socketio.emit('switch_change', {
            'switch': color,
            'active': active,
            'timestamp': time.time()
        })
    
    def emit_encoder_change(self, encoder_id, delta):
        """Emit encoder change event"""
        self.encoders[encoder_id] += delta
        direction = "right" if delta > 0 else "left"
        self.socketio.emit('encoder_change', {
            'encoder_id': encoder_id,
            'value': self.encoders[encoder_id],
            'direction': direction,
            'timestamp': time.time()
        })
    
    def emit_encoder_button_press(self, encoder_id):
        """Emit encoder button press event"""
        self.encoders[encoder_id] = 0
        self.socketio.emit('encoder_button_press', {
            'encoder_id': encoder_id,
            'timestamp': time.time()
        })

# Global server instance
server = SimulatorServer(socketio)

@socketio.on('connect')
def handle_connect():
    server.connected_clients += 1
    print(f'\n=== CLIENT CONNECTED === (total: {server.connected_clients})')
    print(f'Timestamp: {time.time()}')
    # Send initial state
    emit('initial_state', {
        'key': {'active': server.key_active},
        'switches': {color: {'active': active} for color, active in server.switches.items()},
        'encoders': server.encoders,
        'timestamp': time.time()
    })
    print('Initial state sent')

@socketio.on('disconnect')
def handle_disconnect():
    server.connected_clients -= 1
    print(f'\n=== CLIENT DISCONNECTED === (total: {server.connected_clients})')

@app.route('/')
def index():
    return "Cyberdeck Mac Simulator - Connect via Socket.IO client", 200

@app.route('/status')
def status():
    return {
        'connected_clients': server.connected_clients,
        'key': server.key_active,
        'switches': server.switches,
        'encoders': server.encoders
    }

def draw_ui(stdscr, server):
    """Draw the UI showing current state and controls"""
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(True)  # Non-blocking input
    
    # Color pairs
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)
    
    def safe_addstr(y, x, text, attr=0):
        """Safely add string only if it fits on screen"""
        try:
            if y < height - 1 and x < width:
                stdscr.addstr(y, x, text[:width-x-1], attr)
        except:
            pass
    
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Check minimum size
        if height < 20 or width < 50:
            safe_addstr(0, 0, "Terminal too small!", curses.A_BOLD)
            safe_addstr(1, 0, f"Need 20x50, have {height}x{width}")
            safe_addstr(2, 0, "Please resize your terminal")
            stdscr.refresh()
            time.sleep(0.1)
            key = stdscr.getch()
            if key == 27:  # ESC
                break
            continue
        
        # Title
        title = "CYBERDECK MAC SIMULATOR"
        safe_addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        
        # Connection status
        clients = server.connected_clients
        status = f"{clients} CLIENT{'S' if clients != 1 else ''} CONNECTED"
        color = curses.color_pair(1) if clients > 0 else curses.color_pair(4)
        safe_addstr(1, (width - len(status)) // 2, status, color | curses.A_BOLD)
        
        line = 3
        
        # Instructions header
        safe_addstr(line, 2, "CONTROLS:", curses.A_BOLD | curses.A_UNDERLINE)
        line += 2
        
        # Key button
        safe_addstr(line, 2, "Main Button:", curses.A_BOLD)
        line += 1
        key_status = "RELEASED" if server.key_active else "PRESSED"
        key_color = curses.color_pair(1) if server.key_active else curses.color_pair(3)
        safe_addstr(line, 4, f"[K] Toggle Key - Current: {key_status}", key_color)
        line += 2
        
        # Switches
        safe_addstr(line, 2, "Switches:", curses.A_BOLD)
        line += 1
        for i, (color_name, active) in enumerate(server.switches.items()):
            status = "RELEASED" if active else "PRESSED"
            color = curses.color_pair(1) if active else curses.color_pair(3)
            key = ['G', 'B', 'R'][i]
            color_display = color_name.upper()
            safe_addstr(line, 4, f"[{key}] {color_display:6s} - {status}", color)
            line += 1
        line += 1
        
        # Encoders
        safe_addstr(line, 2, "Rotary Encoders:", curses.A_BOLD)
        line += 1
        
        encoder_keys = [
            ("1", "1/2", "Encoder 1"),
            ("2", "Q/W", "Encoder 2"),
            ("3", "A/S", "Encoder 3"),
            ("4", "Z/X", "Encoder 4")
        ]
        
        for enc_id, keys, label in encoder_keys:
            value = server.encoders[int(enc_id)]
            safe_addstr(line, 4, f"[{keys}] {label:10s} - Value: {value:4d}", curses.color_pair(5))
            line += 1
        
        line += 1
        
        # Encoder buttons
        safe_addstr(line, 2, "Encoder Buttons:", curses.A_BOLD)
        line += 1
        safe_addstr(line, 4, "[3][E][D][C] Reset Encoder 1/2/3/4", curses.color_pair(4))
        line += 2
        
        # Arrow key alternative
        safe_addstr(line, 2, "Arrows: UP/DOWN=Enc1, LEFT/RIGHT=Enc2", curses.A_DIM)
        line += 2
        
        # Exit
        safe_addstr(line, 2, "[ESC] Exit", curses.color_pair(3) | curses.A_BOLD)
        
        stdscr.refresh()
        
        # Handle input
        try:
            key = stdscr.getch()
            
            if key == 27:  # ESC
                break
            elif key == ord('k') or key == ord('K'):
                # Toggle key button
                server.emit_key_change(not server.key_active)
            elif key == ord('g') or key == ord('G'):
                # Toggle green switch
                server.emit_switch_change('green', not server.switches['green'])
            elif key == ord('b') or key == ord('B'):
                # Toggle blue switch
                server.emit_switch_change('blue', not server.switches['blue'])
            elif key == ord('r') or key == ord('R'):
                # Toggle red switch
                server.emit_switch_change('red', not server.switches['red'])
            # Encoder 1
            elif key == ord('1') or key == curses.KEY_DOWN:
                server.emit_encoder_change(1, -1)
            elif key == ord('2') or key == curses.KEY_UP:
                server.emit_encoder_change(1, 1)
            elif key == ord('3'):
                server.emit_encoder_button_press(1)
            # Encoder 2
            elif key == ord('q') or key == ord('Q') or key == curses.KEY_LEFT:
                server.emit_encoder_change(2, -1)
            elif key == ord('w') or key == ord('W') or key == curses.KEY_RIGHT:
                server.emit_encoder_change(2, 1)
            elif key == ord('e') or key == ord('E'):
                server.emit_encoder_button_press(2)
            # Encoder 3
            elif key == ord('a') or key == ord('A'):
                server.emit_encoder_change(3, -1)
            elif key == ord('s') or key == ord('S'):
                server.emit_encoder_change(3, 1)
            elif key == ord('d') or key == ord('D'):
                server.emit_encoder_button_press(3)
            # Encoder 4
            elif key == ord('z') or key == ord('Z'):
                server.emit_encoder_change(4, -1)
            elif key == ord('x') or key == ord('X'):
                server.emit_encoder_change(4, 1)
            elif key == ord('c') or key == ord('C'):
                server.emit_encoder_button_press(4)
            
        except KeyboardInterrupt:
            break
        
        time.sleep(0.05)  # 50ms refresh rate

def main():
    import os
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Cyberdeck Hardware Mac Simulator')
    parser.add_argument('--port', type=int, default=3001, help='Port to run the socket server on (default: 3001)')
    args = parser.parse_args()
    
    print("Cyberdeck Mac Simulator Starting...")
    print("=" * 40)
    print(f"Socket server running on http://localhost:{args.port}")
    print("Connect your client to receive events")
    print("\nThis simulator broadcasts the same socket events as the real hardware:")
    print("  - key_change")
    print("  - switch_change") 
    print("  - encoder_change")
    print("  - encoder_button_press")
    
    # Check if we're in an interactive terminal
    is_interactive = sys.stdin.isatty() and sys.stdout.isatty()
    
    if is_interactive:
        print("\nStarting interactive CLI...")
        time.sleep(1)
        
        # Start Flask-SocketIO server in a separate thread
        server_thread = Thread(
            target=lambda: socketio.run(app, host='0.0.0.0', port=args.port, debug=False, allow_unsafe_werkzeug=True),
            daemon=True
        )
        server_thread.start()
        
        # Give server time to start
        time.sleep(1)
        
        # Start curses UI
        try:
            curses.wrapper(draw_ui, server)
        except KeyboardInterrupt:
            pass
        finally:
            print("\nSimulator stopped.")
    else:
        print("\nRunning in headless mode (no interactive terminal detected)")
        print("\nControls:")
        print("  Press K in terminal for key toggle")
        print("  Press G/B/R for switches")
        print("  Press 1/2, Q/W, A/S, Z/X for encoders")
        print("  Press Ctrl+C to stop")
        print()
        
        # Start Flask-SocketIO server (blocking)
        try:
            socketio.run(app, host='0.0.0.0', port=args.port, debug=False, allow_unsafe_werkzeug=True)
        except KeyboardInterrupt:
            print("\nSimulator stopped.")

if __name__ == "__main__":
    main()

