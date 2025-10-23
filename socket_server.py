#!/usr/bin/env python3
"""
Socket-enabled Firmware Script for Raspberry Pi
- Emits socket events on every input change
- 3 Switches on GPIO 18, 20, 21
- 4 Rotary Encoders with buttons
- 1 Button on GPIO 2
"""

import time
import os
import RPi.GPIO as GPIO
import signal
import sys
from flask import Flask
from flask_socketio import SocketIO, emit
from threading import Thread

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

class ButtonMonitor:
    def __init__(self, socketio):
        self.button_pin = 2  # GPIO 2 (Physical Pin 3)
        self.socketio = socketio
        self.last_state = None
        
    def setup_gpio(self):
        """Setup GPIO for button monitoring"""
        try:
            GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            print(f"Button monitor initialized on GPIO {self.button_pin}")
        except Exception as e:
            print(f"Error setting up button monitor: {e}")
    
    def get_button_status(self):
        """Get current button state - returns True when released, False when pressed"""
        try:
            state = GPIO.input(self.button_pin)
            return True if state == GPIO.HIGH else False
        except:
            return None
    
    def check_and_emit(self):
        """Check button state and emit if changed"""
        current_state = self.get_button_status()
        if current_state != self.last_state:
            self.last_state = current_state
            self.socketio.emit('key_change', {
                'active': current_state,
                'timestamp': time.time()
            })

class SwitchMonitor:
    def __init__(self, socketio):
        self.pins = {
            18: 530,  # GPIO 18 -> sysfs 530 (Green)
            20: 532,  # GPIO 20 -> sysfs 532 (Blue)
            21: 533   # GPIO 21 -> sysfs 533 (Red)
        }
        self.colors = {
            18: "green",
            20: "blue",
            21: "red"
        }
        self.switch_states = {}
        self.socketio = socketio
        self.export_gpio_pins()
        # Initialize last states
        self.last_states = self.get_switch_states()
        
    def export_gpio_pins(self):
        """Export GPIO pins for switches if not already exported"""
        for gpio_num, sysfs_num in self.pins.items():
            try:
                # Check if pin is already exported
                with open(f'/sys/class/gpio/gpio{sysfs_num}/value', 'r') as f:
                    pass  # If this succeeds, pin is already exported
            except FileNotFoundError:
                # Pin not exported, export it
                try:
                    with open('/sys/class/gpio/export', 'w') as f:
                        f.write(str(sysfs_num))
                    print(f"Exported GPIO {gpio_num} (sysfs {sysfs_num})")
                    
                    # Set direction to input
                    with open(f'/sys/class/gpio/gpio{sysfs_num}/direction', 'w') as f:
                        f.write('in')
                    print(f"Set GPIO {gpio_num} direction to input")
                    
                except Exception as e:
                    print(f"Failed to export GPIO {gpio_num} (sysfs {sysfs_num}): {e}")
            except Exception as e:
                print(f"Error checking GPIO {gpio_num} (sysfs {sysfs_num}): {e}")
        
    def read_gpio(self, pin):
        """Read the value of a GPIO pin"""
        try:
            with open(f'/sys/class/gpio/gpio{pin}/value', 'r') as f:
                return f.read().strip()
        except:
            return 'Error'
    
    def get_switch_states(self):
        """Get current state of all switches - returns True when released, False when pressed"""
        states = {}
        for gpio_num, sysfs_num in self.pins.items():
            value = self.read_gpio(sysfs_num)
            if value == "1":
                status = True  # Released
            elif value == "0":
                status = False  # Pressed
            else:
                status = None  # Error
            states[gpio_num] = {
                'value': value,
                'status': status
            }
        return states
    
    def check_and_emit(self):
        """Check switch states and emit if any changed"""
        current_states = self.get_switch_states()
        for gpio_num in current_states:
            if current_states[gpio_num]['status'] != self.last_states[gpio_num]['status']:
                self.socketio.emit('switch_change', {
                    'switch': self.colors[gpio_num],
                    'active': current_states[gpio_num]['status'],
                    'timestamp': time.time()
                })
        self.last_states = current_states

class RotaryEncoder:
    def __init__(self, encoder_id, pin_a, pin_b, pin_button, socketio):
        self.encoder_id = encoder_id
        self.pin_a = pin_a
        self.pin_b = pin_b
        self.pin_button = pin_button
        self.socketio = socketio
        
        # Encoder state variables
        self.counter = 0
        self.last_counter = 0
        self.last_a = 0
        self.last_b = 0
        self.last_button = 1
        self.last_encoder_time = 0
        self.last_button_time = 0
        self.encoder_debounce_delay = 0.001  # 1ms - very responsive for fast rotation
        self.button_debounce_delay = 0.2
        
    def setup_gpio(self):
        """Initialize GPIO pins"""
        try:
            # Setup encoder pins as inputs with pull-up resistors
            GPIO.setup(self.pin_a, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.pin_b, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Setup button pin as input with pull-up resistor (only if button exists)
            if self.pin_button is not None:
                GPIO.setup(self.pin_button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Read initial states
            self.last_a = GPIO.input(self.pin_a)
            self.last_b = GPIO.input(self.pin_b)
            self.last_button = GPIO.input(self.pin_button) if self.pin_button else 1
            
            print(f"Encoder {self.encoder_id} GPIO setup successful")
            
        except Exception as e:
            print(f"GPIO setup error for encoder {self.encoder_id}: {e}")
            print(f"Failed pins: A={self.pin_a}, B={self.pin_b}, Button={self.pin_button}")
            return False
        return True

    def update(self, current_time):
        """Update encoder state by polling - using proven algorithm from test file"""
        try:
            current_a = GPIO.input(self.pin_a)
            current_b = GPIO.input(self.pin_b)
            current_button = GPIO.input(self.pin_button) if self.pin_button else 1
            
            # Check if A pin changed (quadrature logic with debouncing)
            if current_a != self.last_a:
                if current_time - self.last_encoder_time > self.encoder_debounce_delay:
                    # Determine direction based on A and B states (quadrature decoding)
                    if current_a == 1:  # A rising edge
                        if current_b == 0:
                            self.counter += 1  # Clockwise
                        else:
                            self.counter -= 1  # Counter-clockwise
                    else:  # A falling edge
                        if current_b == 1:
                            self.counter += 1  # Clockwise
                        else:
                            self.counter -= 1  # Counter-clockwise
                    
                    self.last_encoder_time = current_time
                
                # Always update last A state to track changes
                self.last_a = current_a
            
            # Update B state separately
            self.last_b = current_b
            
            # Check button state (if button exists)
            button_pressed = False
            if self.pin_button:
                if current_button == 0 and self.last_button == 1:
                    if current_time - self.last_button_time > self.button_debounce_delay:
                        self.last_button_time = current_time
                        self.counter = 0
                        button_pressed = True
                
                self.last_button = current_button
            
            # Emit if counter changed
            if self.counter != self.last_counter:
                delta = self.counter - self.last_counter
                direction = "right" if delta > 0 else "left"
                self.socketio.emit('encoder_change', {
                    'encoder_id': self.encoder_id,
                    'value': self.counter,
                    'direction': direction,
                    'timestamp': time.time()
                })
                self.last_counter = self.counter
            
            # Emit if button was pressed
            if button_pressed:
                self.socketio.emit('encoder_button_press', {
                    'encoder_id': self.encoder_id,
                    'timestamp': time.time()
                })
                
        except Exception as e:
            print(f"Encoder {self.encoder_id} error: {e}")
            pass
    
    def get_counter(self):
        """Get current counter value"""
        return self.counter
    
    def reset_counter(self):
        """Reset counter to zero"""
        self.counter = 0
    
    def cleanup(self):
        """Clean up GPIO resources"""
        pass  # Will be handled by main cleanup

class FirmwareManager:
    def __init__(self, socketio):
        self.socketio = socketio
        self.switch_monitor = SwitchMonitor(socketio)
        self.button_monitor = ButtonMonitor(socketio)
        self.encoders = []
        self.setup_gpio()
        self.setup_encoders()
        
    def setup_gpio(self):
        """Initialize GPIO for all components"""
        try:
            # Clean up any existing GPIO setup first
            GPIO.cleanup()
            time.sleep(0.5)  # Longer delay to ensure cleanup is complete
            
            # Set GPIO mode
            GPIO.setmode(GPIO.BCM)
            print("GPIO initialized for all components")
            
            # Setup button monitor GPIO
            self.button_monitor.setup_gpio()
            
        except RuntimeError as e:
            print(f"GPIO setup error: {e}")
            # Try to clean up and retry once
            try:
                GPIO.cleanup()
                time.sleep(1)
                GPIO.setmode(GPIO.BCM)
                print("GPIO re-initialized after cleanup")
                self.button_monitor.setup_gpio()
            except Exception as retry_e:
                print(f"Failed to re-initialize GPIO: {retry_e}")
                sys.exit(1)
        
    def setup_encoders(self):
        """Initialize all 4 encoders"""
        encoder_configs = [
            (3, 4, 17, 19),      # Encoder 3: was ID 1
            (2, 27, 22, 13),     # Encoder 2: unchanged
            (1, 5, 6, 26),       # Encoder 1: was ID 3
            (4, 23, 24, None)    # Encoder 4: unchanged
        ]
        
        successful_encoders = 0
        for config in encoder_configs:
            try:
                encoder = RotaryEncoder(*config, self.socketio)
                if encoder.setup_gpio():
                    self.encoders.append(encoder)
                    successful_encoders += 1
                    print(f"Encoder {config[0]} setup successful")
                else:
                    print(f"Failed to setup encoder {config[0]}")
            except Exception as e:
                print(f"Error creating encoder {config[0]}: {e}")
        
        print(f"\nEncoders initialized: {successful_encoders}/4")
        if successful_encoders > 0:
            print("  Encoder 1: A=GPIO5, B=GPIO6, Button=GPIO26")
            print("  Encoder 2: A=GPIO27, B=GPIO22, Button=GPIO13")
            print("  Encoder 3: A=GPIO4, B=GPIO17, Button=GPIO19")
            print("  Encoder 4: A=GPIO23, B=GPIO24, No Button")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        print("\nStarting monitoring loop...")
        try:
            while True:
                current_time = time.time()
                
                # Check button
                self.button_monitor.check_and_emit()
                
                # Check switches
                self.switch_monitor.check_and_emit()
                
                # Update all encoders
                for encoder in self.encoders:
                    encoder.update(current_time)
                
                # Minimal sleep for fast polling
                time.sleep(0.0001)  # 0.1ms - much faster polling
                
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up all resources"""
        GPIO.cleanup()
        print("\nGPIO cleaned up. Goodbye!")

# Global manager instance
manager = None

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    # Send initial state
    if manager:
        button_state = manager.button_monitor.get_button_status()
        switch_states = manager.switch_monitor.get_switch_states()
        encoder_values = {e.encoder_id: e.counter for e in manager.encoders}
        
        emit('initial_state', {
            'key': {'active': button_state},
            'switches': {manager.switch_monitor.colors[pin]: {'active': state['status']} for pin, state in switch_states.items()},
            'encoders': encoder_values,
            'timestamp': time.time()
        })

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@app.route('/')
def index():
    return "Firmware Socket Server - Connect via Socket.IO client", 200

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\nShutting down...')
    if manager:
        manager.cleanup()
    sys.exit(0)

def main():
    global manager
    
    print("Firmware Socket Monitor Starting...")
    print("====================================")
    print("Button: GPIO 2")
    print("Switches: GPIO 18, 20, 21")
    print("Encoders: 4 rotary encoders with buttons")
    print("\nSocket events will be emitted on every input change")
    print("Socket server running on http://localhost:5000")
    print("Connect your client to receive real-time events")
    print("Press Ctrl+C to stop")
    print()
    
    # Create firmware manager
    manager = FirmwareManager(socketio)
    
    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start monitoring in a separate thread
    monitor_thread = Thread(target=manager.monitor_loop, daemon=True)
    monitor_thread.start()
    
    # Start Flask-SocketIO server
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)

if __name__ == "__main__":
    main()
