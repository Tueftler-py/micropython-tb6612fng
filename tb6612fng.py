# Created by Tueftler.py

import machine, time, asyncio

def percent_to_duty(p):
    """
    Convert a speed percentage to a PWM duty cycle value.

    Args:
        p (float or int): Speed percentage, can be negative (absolute value is used).
                          Value is clipped between 0 and 100.

    Returns:
        int: PWM duty cycle between 0 and 65535 (16-bit resolution).
    """
    p = max(0, min(100, abs(p)))
    return min(round(p * 655.35), 65535)

class TB6612FNG:
    """
    Driver class for TB6612FNG dual motor driver chip, controlling one motor channel.

    Features:
    - Forward and reverse motor direction control
    - PWM speed control with 16-bit resolution
    - Brake and coast modes
    - Optional pin reversal to adjust motor wiring
    - Smooth speed ramping (blocking and async)
    - Standby pin control (optional)

    Designed for MicroPython on RP2040 (Raspberry Pi Pico) but portable to other platforms.
    """
    
    def __init__(self, pin_1, pin_2, pwm_pin, stby_pin=None, pwm_freq=20_000):
        """
        Initialize motor control pins and PWM.

        Args:
            pin_1 (int): GPIO pin number connected to IN1 on TB6612FNG.
            pin_2 (int): GPIO pin number connected to IN2 on TB6612FNG.
            pwm_pin (int): GPIO pin number for PWM speed control.
            stby_pin (int or None): GPIO pin number for standby (enable/disable) control.
                                   Set to None if handled externally or multiple drivers share the pin.
            pwm_freq (int): PWM frequency in Hz, default is 20kHz (high enough to be inaudible).
        """
        self.p1 = machine.Pin(pin_1, machine.Pin.OUT)
        self.p2 = machine.Pin(pin_2, machine.Pin.OUT)
        self.pwm = machine.PWM(pwm_pin, freq=pwm_freq)
        if stby_pin is not None:
            self.stby = machine.Pin(stby_pin, machine.Pin.OUT)
            self.on()
        self.speed = 0
        self.brake()
        
    @micropython.native
    def set_raw_values(self, pin1=None, pin2=None, pwm_duty=None):
        """
        Directly set the IN1, IN2 pins and PWM duty cycle.

        Args:
            pin1 (bool): state of p1 (0 or 1),
            pin2 (bool): state of p2 (0 or 1),
            pwm_duty (int or None): PWM duty cycle (0-65535), or None to leave unchanged.
        """
        if pin1 is not None:
            self.p1.value(pin1)
        if pin2 is not None:
            self.p2.value(pin2)
        if pwm_duty is not None:
            self.pwm.duty_u16(pwm_duty)
            
    def brake(self):
        """
        Actively brake the motor by setting both IN1 and IN2 high and PWM to zero.
        This stops the motor quickly.
        """
        self.set_raw_values(1, 1, 0)
        
    def coast(self):
        """
        Let the motor coast freely (no braking) by setting both IN1 and IN2 low and PWM to zero.
        The motor spins down naturally.
        """
        self.set_raw_values(0, 0, 0)
        
    def set_forward(self):
        """
        Configure pins for forward rotation (IN1=1, IN2=0).
        """
        self.set_raw_values(1, 0)
        
    def set_reverse(self):
        """
        Configure pins for reverse rotation (IN1=0, IN2=1).
        """
        self.set_raw_values(0, 1)
        
    def set_motor(self, direction, speed):
        """
        Set the motor direction and speed.

        Args:
            direction (str): Either 'forward' or 'reverse'.
            speed (int or float): Speed percentage (0-100).
        """
        method = getattr(self, f'set_{direction}', None)
        if method is None:
            raise ValueError(f"Invalid direction: {direction}")
        method()
        duty = percent_to_duty(speed)
        self.set_raw_values(pwm_duty=duty)
        
    @micropython.native
    def drive(self, speed=None, auto_brake=True):
        """
        Drive the motor at a specified speed.

        Args:
            speed (int, float or None): Speed between -100 and 100.
                                        Negative values drive reverse.
                                        Positive values drive forward.
                                        None keeps current speed.
            auto_brake (bool): If True, apply brake when speed is 0.
                               If False, motor will coast when speed is 0.

        Returns:
            Current speed setting (int or float).
        """
        if speed is not None:
            p = max(-100, min(100, speed))
            self.speed = p
            if p != 0:
                self.set_motor("reverse" if p < 0 else "forward", abs(p))
            else:
                self.brake() if auto_brake else self.coast()
        return self.speed
          
    @micropython.native
    def drive_ramp(self, target_speed, status_func=None):
        """
        Generator that gradually changes speed step-by-step to the target speed.

        Args:
            target_speed (int or float): Desired speed (-100 to 100).
            status_func (callable or None): Optional function called with current speed after each step.

        Yields:
            int or float: Current speed after each incremental step.
        """
        while self.drive() != target_speed:
            change = -1 if self.drive() > target_speed else 1
            if status_func:
                status_func(self.drive())
            yield self.drive(self.drive() + change)
        if status_func:
            status_func(self.drive())
          
    def safe_drive(self, target_speed, change_speed=70, status_func=None):
        """
        Gradually change speed to target_speed in a blocking manner.

        Args:
            target_speed (int or float): Target speed (-100 to 100).
            change_speed (int): Delay between steps in milliseconds.
            status_func (callable or None): Optional callback receiving current speed.
        """
        try:
            for _ in self.drive_ramp(target_speed, status_func):
                time.sleep_ms(change_speed)
        except KeyboardInterrupt:
            self.brake()

    async def safe_drive_async(self, target_speed, change_speed=70, status_func=None):
        """
        Gradually change speed to target_speed asynchronously.

        Args:
            target_speed (int or float): Target speed (-100 to 100).
            change_speed (int): Delay between steps in milliseconds.
            status_func (callable or None): Optional callback receiving current speed.
        """
        try:
            for _ in self.drive_ramp(target_speed, status_func):
                await asyncio.sleep_ms(change_speed)
        except KeyboardInterrupt:
            self.brake()

    def on(self):
        """
        Enable the motor driver by setting the standby (STBY) pin high.
        """
        self.stby.value(1)
        
    def off(self, auto_brake=True):
        """
        Disable the motor driver by setting the standby pin low.

        Args:
            auto_brake (bool): If True, brake the motor before disabling.
                               If False, let the motor coast before disabling.
        """
        if auto_brake:
            self.brake()
        else:
            self.coast()
        self.stby.value(0)
