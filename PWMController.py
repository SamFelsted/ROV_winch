# pyright: reportMissingImports=false

import pwmio
import board

class PWMController:

    def __init__(
            self,
            pwmFrequency,
            pwmPinID,
            pwmDutyCycle
    ):
        
        self.pwmFrequency = pwmFrequency
        self.pwmDutyCycle = pwmDutyCycle

        pin_obj = getattr(board, f'D{pwmPinID}')
        self.pwmPin = pwmio.PWMOut(pin_obj, frequency=pwmFrequency, duty_cycle=pwmDutyCycle)

    def setDuty(self, duty):
        """
        :param duty: 0 to 255
        """
        scaled_duty = int(duty * 65535 / 255)
        self.pwmPin.duty_cycle = scaled_duty
        print(f"Duty Cycle set to {duty} (scaled: {scaled_duty})")


            
