# pyright: reportMissingImports=false
import time
import board
import busio
from digitalio import DigitalInOut, Direction, Pull  # GPIO module
import adafruit_mcp4725

import const
import util


class Actuator:
    def __init__(
            self,
            ON_OFF_pin,
            direction_pin,
            feedback_pin
    ):

        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.dac = adafruit_mcp4725.MCP4725(self.i2c, address=0x60)

        self.ON = DigitalInOut(eval('board.D' + str(ON_OFF_pin)))
        self.ON.direction = Direction.OUTPUT

        self.direction = DigitalInOut(eval('board.D' + str(direction_pin)))
        self.direction.direction = Direction.OUTPUT

        # optical feedback from the actuator:
        self.feedback = DigitalInOut(eval('board.D' + str(feedback_pin)))
        self.feedback.direction = Direction.INPUT

        self.ON.value = 0
        self.activeSpeed = 0
        self.currentPulses = 0
        self.prior_feedback_val = self.feedback.value

        self.feedback.pull = Pull.UP
        self.last_pulse_time = time.time() - const.Actuator.false_pulse_delay_actuator

        self.time_init = time.time()

        self.infp = open('/home/pi/ROV_winch_sam/stacking_state.txt', 'r+')
        self.lineSpeedState = 0  # float(self.infp.read())
        self.absolutePosition = 0

    def updatePosition(self):
        """
        Count actuator feedback pulses
        """
        print(self.currentPulses)
        current_feedback_value = self.feedback.value
        if not current_feedback_value and self.prior_feedback_val:
            self.currentPulses = self.currentPulses + 1
        self.prior_feedback_val = current_feedback_value

    def zeroPosition(self):
        self.absolutePosition = 0

    def writeSpeed(self):
        """
        Writes the speed to the motor and logs it
        """
        self.infp.write(f"{self.activeSpeed}")
        self.dac.normalized_value = self.activeSpeed

    def setSpeed(self, value):
        """
        Sets actuator Speed
        :param value: motor percent (0 to 1)
        """
        if value == 0:
            print("Wind actuator off")
            self.ON.value = 0
            return

        print("Wind actuator on")
        self.ON.value = 1
        self.activeSpeed = util.clamp(abs(value), 0, 1)
        self.writeSpeed()

    def setDirection(self, direction):
        """
        sets direction pin value
        :param direction: (0 or 1)
        """
        self.direction.value = direction

    def changeDirection(self):
        """
        Reverses direction of actuator
        """
        if self.direction.value == const.Actuator.RETRACT:
            self.direction.value = const.Actuator.EXTEND
        else:
            self.direction.value = const.Actuator.RETRACT

    def manualAdjust(self, distance):
        """
        :param distance (inches)
        """
        print('level wind adjusting ' + distance + ' inches :)')
        self.move(float(distance))

    def moveCableDistance(self):
        """
        Move the actuator one cable width
        :return:
        """
        self.move(const.Actuator.cableDiameter)

    def move(self, distance):  # default to cable diameter
        """
        :param distance: inches
        """
        self.currentPulses = 0  # zero position tracker
        targetPulses = util.inchesToPulses(distance)

        speed, direction = util.calculateActuatorSpeed(distance)
        print(speed, direction)
        self.setSpeed(speed)  # write a speed
        self.setDirection(direction)

        self.time_init = time.time()
        self.last_pulse_time = self.time_init * 1000

        stationary_counter = 0
        prior_position = 0
        # check counted pulses every 50 ms.
        while abs(self.currentPulses) <= abs(targetPulses):
            self.updatePosition()
            if self.currentPulses == prior_position:  # if actuator is not moving
                stationary_counter += 1
                if stationary_counter > 40:
                    print(f"Not moving: {stationary_counter}")
            else:
                stationary_counter = 0

            prior_position = self.currentPulses

            if stationary_counter > 50:
                print("hit wall :(")
                break

        self.setSpeed(0)