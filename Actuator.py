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
            feedback_pin,
            readSwitchMinPin,
            readSwitchMaxPin
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
        self.feedback.pull = Pull.UP

        self.ON.value = 0
        self.activeSpeed = 0
        self.currentPulses = 0
        self.prior_feedback_val = self.feedback.value

        # Stuff for direction logic
        infp = open('/home/pi/ROV_winch/stacking_state.txt', 'r')
        self.currentForwardDirection = int(infp.read())
        infp.close()

        self.lastReadTime = time.time()
        self.readCount = 0

        # Min, max reedswitch setup
        self.logic_high = DigitalInOut(board.D12)
        self.logic_high.direction = Direction.OUTPUT
        self.logic_high.value = 1

        self.readSwitchMin = DigitalInOut(eval('board.D' + str(readSwitchMinPin)))
        self.readSwitchMin.direction = Direction.INPUT
        self.readSwitchMin.pull = Pull.DOWN

        self.readSwitchMax = DigitalInOut(eval('board.D' + str(readSwitchMaxPin)))
        self.readSwitchMax.direction = Direction.INPUT
        self.readSwitchMax.pull = Pull.DOWN

    def updatePosition(self):
        """
        Count actuator feedback pulses
        """
        current_feedback_value = self.feedback.value
        if not current_feedback_value and self.prior_feedback_val:
            self.currentPulses = self.currentPulses + 1
        self.prior_feedback_val = current_feedback_value

    def writeSpeed(self):
        """
        Writes the speed to the motor and logs it
        """
        self.dac.normalized_value = self.activeSpeed

    def setSpeed(self, value):
        """
        Sets actuator Speed
        :param value: motor percent (0 to 1)
        """
        if value == 0:
            self.ON.value = 0
            return

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
        self.currentForwardDirection = util.flipBit(self.direction.value)
        with open('/home/pi/ROV_winch/stacking_state.txt', 'w') as infp:
            infp.write(str(self.currentForwardDirection))
            infp.close()

    def manualAdjust(self, distance):
        """
        :param distance (inches)
        """
        print('level wind adjusting ' + distance + ' inches :)')
        self.move(float(distance), True)

    def moveCableDistance(self, winchDirection):
        """

        Move the actuator one cable width
        :param winchDirection: direction of ROV winch, 1 is forward and -1 is backward
        :return:
        """

        self.move(const.Actuator.cableDiameter * winchDirection, False)

    def checkReadSwitch(self):
        if (self.readSwitchMin.value and self.currentForwardDirection == 1) or (
                self.readSwitchMax.value and self.currentForwardDirection == 0):

            self.lastReadTime = time.time()
            # print("Min: " + str(self.readSwitchMin.value) + "\nMax: " + str(self.readSwitchMax.value))
            if self.readCount > 50 and abs(self.lastReadTime - time.time()) < 1:
                self.readCount = 0
                return True

            self.readCount += 1
            return False

    def debug(self, targetPulses):
        print("Actuator pos: " + str(self.currentPulses))
        print("Wanted pos: " + str(targetPulses))

    def move(self, distance, manualOverride):  # default to cable diameter
        """
        :param distance: inches
        :param manualOverride:
        """
        self.currentPulses = 0  # zero position tracker
        targetPulses = util.inchesToPulses(distance)

        # calculations for direction
        speed, direction = util.calculateActuatorState(distance,  self.currentForwardDirection, manualOverride)

        self.setSpeed(speed)  # write a speed
        self.setDirection(direction)

        stationary_counter = 0
        prior_position = 0
        # check counted pulses every 50 ms, main control loop
        while abs(self.currentPulses) <= abs(targetPulses):
            self.updatePosition()

            if self.currentPulses == prior_position:  # if actuator is not moving
                stationary_counter += 1
            else:
                stationary_counter = 0

            prior_position = self.currentPulses

            if stationary_counter > 50:
                print("hit wall :(")
                break

            if self.checkReadSwitch():
                self.changeDirection()
                break

        self.setSpeed(0)
