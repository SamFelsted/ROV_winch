# pyright: reportMissingImports=false

import pigpio
import time
from digitalio import DigitalInOut, Direction, Pull  # GPIO module



class PWMController:

    def __init__(
            self,
            pwmFrequency,
            pwmPin,
            pwmDutyCycle
    ):
        
        self.pwmFrequency = pwmFrequency
        self.pwmPin = pwmPin
        self.pwmDutyCycle = pwmDutyCycle

        self.pi = pigpio.pi()
        # Set PWM on the pin with specified frequency and duty cycle
        self.pi.set_PWM_frequency(pwmPin, pwmFrequency)          # Look up safe range
        self.pi.set_PWM_dutycycle(pwmPin, 0)  
        

    def setDuty(self, duty):
        """
        :param duty (0 to 255)
        """
        self.pi.set_PWM_dutycycle(self.pwmPin, self.pwmDutyCycle)
            
