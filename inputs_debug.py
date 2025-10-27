#!/usr/bin/env python3
"""
Combined Firmware Script for Raspberry Pi
- 3 Switches on GPIO 18, 20, 21
- 4 Rotary Encoders with buttons
"""

import time
import os
import RPi.GPIO as GPIO
import signal
import sys

class ButtonMonitor:
    def __init__(self):
        self.button_pin = 2  # GPIO 2 (Physical Pin 3)
        # GPIO setup will be handled by main manager
        
    def setup_gpio(self):
        """Setup GPIO for button monitoring"""
        try:
            GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            print(f"Button monitor initialized on GPIO {self.button_pin}")
        except Exception as e:
            print(f"Error setting up button monitor: {e}")
    
    def get_button_status(self):
        """Get current button state"""
        try:
            state = GPIO.input(self.button_pin)
            return "PRESSED" if state == GPIO.LOW else "RELEASED"
        except:
            return "ERROR"

class SwitchMonitor:
    def __init__(self):
        self.pins = {
            18: 530,  # GPIO 18 -> sysfs 530
            20: 532,  # GPIO 20 -> sysfs 532
            21: 533   # GPIO 21 -> sysfs 533
        }
        self.switch_states = {}
        self.export_gpio_pins()
        
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
        """Get current state of all switches"""
        states = {}
        for gpio_num, sysfs_num in self.pins.items():
            value = self.read_gpio(sysfs_num)
            status = "PRESSED" if value == "0" else "RELEASED" if value == "1" else "ERROR"
            states[gpio_num] = {
                'value': value,
                'status': status
            }
        return states

class RotaryEncoder:
    def __init__(self, encoder_id, pin_a, pin_b, pin_button):
        self.encoder_id = encoder_id
        self.pin_a = pin_a
        self.pin_b = pin_b
        self.pin_button = pin_button
        
        # Encoder state variables
        self.counter = 0
        self.last_a = 0
        self.last_b = 0
        self.last_button = 1
        self.last_encoder_time = 0
        self.last_button_time = 0
        self.encoder_debounce_delay = 0.001  # 1ms - very responsive for fast rotation
        self.button_debounce_delay = 0.2
        
        # GPIO setup will be called separately
        
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
            # Don't exit, just skip this encoder
            return False
        return True


    def update(self, current_time):
        """Update encoder state by polling - using proven algorithm from test file"""
        try:
            current_a = GPIO.input(self.pin_a)
            current_b = GPIO.input(self.pin_b)
            current_button = GPIO.input(self.pin_button) if self.pin_button else 1
            
            # Check if A pin changed (quadrature logic with debouncing)
            # Only react to A pin changes to reduce noise
            if current_a != self.last_a:
                if current_time - self.last_encoder_time > self.encoder_debounce_delay:
                    # Determine direction based on A and B states (quadrature decoding)
                    # Read B immediately without extra delay for faster response
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
                    
                    # Prevent counter from going negative
                    if self.counter < 0:
                        self.counter = 0
                    
                    self.last_encoder_time = current_time
                
                # Always update last A state to track changes
                self.last_a = current_a
            
            # Update B state separately
            self.last_b = current_b
            
            # Check button state (if button exists)
            if self.pin_button:
                if current_button == 0 and self.last_button == 1:
                    if current_time - self.last_button_time > self.button_debounce_delay:
                        self.last_button_time = current_time
                        self.counter = 0
                
                self.last_button = current_button
                
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
    def __init__(self):
        self.switch_monitor = SwitchMonitor()
        self.button_monitor = ButtonMonitor()
        self.encoders = []
        self.last_display_state = None
        self.setup_gpio()
        self.setup_encoders()
        self.setup_encoder_events()
        
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
        # Encoder 1: A=4, B=17, Button=19
        # Encoder 2: A=27, B=22, Button=13  
        # Encoder 3: A=5, B=6, Button=26
        # Encoder 4: A=23, B=24, No Button
        encoder_configs = [
            (1, 4, 17, 19),
            (2, 27, 22, 13), 
            (3, 5, 6, 26),
            (4, 23, 24, None)
        ]
        
        successful_encoders = 0
        for config in encoder_configs:
            try:
                encoder = RotaryEncoder(*config)
                if encoder.setup_gpio():  # Check if setup was successful
                    self.encoders.append(encoder)
                    successful_encoders += 1
                    print(f"Encoder {config[0]} setup successful")
                else:
                    print(f"Failed to setup encoder {config[0]}")
            except Exception as e:
                print(f"Error creating encoder {config[0]}: {e}")
        
        print(f"\nEncoders initialized: {successful_encoders}/4")
        if successful_encoders > 0:
            print("  Encoder 1: A=GPIO4, B=GPIO17, Button=GPIO19")
            print("  Encoder 2: A=GPIO27, B=GPIO22, Button=GPIO13")
            print("  Encoder 3: A=GPIO5, B=GPIO6, Button=GPIO26")
            print("  Encoder 4: A=GPIO23, B=GPIO24, No Button")
            print("  Range: 0-100 (press button to reset, except encoder 4)")
        else:
            print("No encoders could be initialized!")
    
    def setup_encoder_events(self):
        """Removed event detection - using fast polling instead for better reliability"""
        pass
    
    def get_current_state(self):
        """Get current state of all components for comparison"""
        button_status = self.button_monitor.get_button_status()
        switch_states = self.switch_monitor.get_switch_states()
        encoder_values = [encoder.counter for encoder in self.encoders]
        
        return (button_status, tuple(sorted(switch_states.items())), tuple(encoder_values))
    
    def display_status(self):
        """Display current status of switches and encoders"""
        # Only update if state has changed
        current_state = self.get_current_state()
        if current_state == self.last_display_state:
            return
        
        self.last_display_state = current_state
        
        # Clear screen
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("Firmware Monitor")
        print("================")
        print(f"Time: {time.strftime('%H:%M:%S')}")
        print()
        
        # Display button
        print("Button:")
        button_status = current_state[0]
        print(f"  GPIO  2: {button_status}")
        
        print()
        
        # Display switches
        print("Switches:")
        switch_states = self.switch_monitor.get_switch_states()
        for gpio_num in sorted(switch_states.keys()):
            state = switch_states[gpio_num]
            print(f"  GPIO {gpio_num}: {state['status']}")
        
        print()
        
        # Display encoders
        print("Rotary Encoders:")
        if len(self.encoders) > 0:
            for encoder in self.encoders:
                print(f"  Encoder {encoder.encoder_id}: {encoder.counter:3d}")
        else:
            print("  No encoders available")
        
        print()
        print("Press button, switches and rotate encoders to test!")
        print("Press Ctrl+C to exit")
    
    def cleanup(self):
        """Clean up all resources"""
        GPIO.cleanup()
        print("\nGPIO cleaned up. Goodbye!")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\nShutting down...')
    manager.cleanup()
    sys.exit(0)

def main():
    global manager
    
    print("Firmware Monitor Starting...")
    print("============================")
    print("Button: GPIO 2")
    print("Switches: GPIO 18, 20, 21")
    print("Encoders: 4 rotary encoders with buttons")
    print("Press Ctrl+C to stop")
    print()
    
    # Create firmware manager
    manager = FirmwareManager()
    
    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Main loop
        while True:
            current_time = time.time()
            
            # Update all encoders with current time
            for encoder in manager.encoders:
                encoder.update(current_time)
            
            manager.display_status()
            # Minimal sleep for fast polling - critical for catching fast rotations
            time.sleep(0.0001)  # 0.1ms - much faster polling
            
    except KeyboardInterrupt:
        pass
    finally:
        manager.cleanup()

if __name__ == "__main__":
    main()