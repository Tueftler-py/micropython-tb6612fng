# TB6612FNG Motor Driver Library for MicroPython

A simple and efficient MicroPython library to control DC motor(s) using the TB6612FNG motor driver chip with RP2040-based boards (e.g. Raspberry Pi Pico), may work on other MicroPython boards as well.

---

## Features

- Control motor direction (forward/reverse)
- Speed control from -100 to 100 (%)
- Brake and coast modes
- Support for reversing motor wiring via software
- Smooth speed ramping with synchronous and asynchronous methods
- Configurable PWM frequency (default 20 kHz for silent operation)
- Optional standby (enable/disable) pin control

---

## Installation

Simply copy the `tb6612fng.py` file into your MicroPython project directory or 'lib' folder.

---

## Usage Example

| Method            | Parameter      | Type            | Default   | Description                                                  |
|-------------------|----------------|-----------------|-----------|--------------------------------------------------------------|
| `__init__`        | `pin_1`        | int             | —         | GPIO pin number for motor input IN1                          |
|                   | `pin_2`        | int             | —         | GPIO pin number for motor input IN2                          |
|                   | `pwm_pin`      | int             | —         | GPIO pin number for PWM control                              |
|                   | `stby_pin`     | int or None     | None      | GPIO pin for standby (enable/disable), None if shared or external |
|                   | `reverse_pins` | bool            | False     | Swap input pins to reverse motor direction                   |
|                   | `pwm_freq`     | int             | 20,000    | PWM frequency in Hz (default 20kHz for silent operation)     |
| `drive`           | `speed`        | int or float    | None      | Speed from -100 to 100; negative = reverse, positive = forward |
|                   | `auto_brake`   | bool            | True      | Automatically brake when speed is 0                          |
| `safe_drive`      | `target_speed` | int or float    | —         | Desired target speed (-100 to 100)                           |
|                   | `change_speed` | int             | 70        | Delay in milliseconds between speed steps                    |
|                   | `status_func`  | callable or None| None      | Optional callback function to receive status updates during ramping |
| `safe_drive_async`| `target_speed` | int or float    | —         | Desired target speed (-100 to 100)                           |
|                   | `change_speed` | int             | 70        | Delay in milliseconds between speed steps                    |
|                   | `status_func`  | callable or None| None      | Optional async callback function to receive status updates during ramping |


Examples:

```python
from tb6612fng import TB6612FNG
import time
import asyncio

# Initialize motor driver for channel 1
motor1 = TB6612FNG(pin_1=15, pin_2=14, pwm_pin=13, stby_pin=12, reverse_pins=False)

# Initialize motor driver for channel 2 (standby pin shared or externally handled)
motor2 = TB6612FNG(pin_1=17, pin_2=16, pwm_pin=18, stby_pin=None, reverse_pins=False)

# Run motor1 forward at 50% speed
motor1.drive(50)
time.sleep(2)

# Gradually ramp motor2 speed to -80% synchronously
motor2.safe_drive(-80, change_speed=50)

# Asynchronous ramp on motor1 to 0 speed
async def stop_motor():
    await motor1.safe_drive_async(0, change_speed=30)

asyncio.run(stop_motor())

# Brake motor1 immediately
motor1.brake()
time.sleep(1)

# Let motor2 coast (free run)
motor2.coast()
