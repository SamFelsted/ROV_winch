# pyright: reportMissingImports=false
import time
import board
import busio
from digitalio import DigitalInOut, Direction, Pull  # GPIO module
import adafruit_mcp4725
from threading import Thread

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
        self.stationary_counter = 0

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

        Thread(daemon=True, target=self.updatePosition).start()

    def updatePosition(self):
        """
        Count actuator feedback pulses
        """
        while True:
            current_feedback_value = self.feedback.value
            if not current_feedback_value and self.prior_feedback_val:
                self.currentPulses = self.currentPulses + 1
                self.stationary_counter = 0
            elif current_feedback_value == self.prior_feedback_val:
                self.stationary_counter += 1
            self.prior_feedback_val = current_feedback_value
            time.sleep(0.0001)

    def updatePosition_off(self):
        """
            Algorithm based on debounce.c written by Kenneth A. Kuhn
        """
        DEBOUNCE_TIME = 0.0003
        SAMPLE_FREQUENCY = 10000
        MAXIMUM = DEBOUNCE_TIME * SAMPLE_FREQUENCY
        integrator = 0
        output = 0
        prior_output = 0

        while True:
            time.sleep(1 / SAMPLE_FREQUENCY)
            input = self.feedback.value
            if input == 0:
                if integrator > 0:
                    integrator = integrator - 1
            elif integrator < MAXIMUM:
                integrator = integrator + 1
            if integrator == 0:
                output = 0
            elif integrator >= MAXIMUM:
                output = 1
                integrator = MAXIMUM
            if output == 0 and prior_output == 1:
                self.currentPulses = self.currentPulses + 1
            prior_output = output

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
        self.currentForwardDirection = util.flipBit(self.currentForwardDirection)
        with open('/home/pi/ROV_winch/stacking_state.txt', 'w') as infp:
            infp.write(str(self.currentForwardDirection))
            infp.close()

    def manualAdjust(self, distance, winchDirection):
        """
        :param winchDirection:
        :param distance (inches)
        """
        print('level wind adjusting ' + distance + ' inches :)')
        self.move(float(distance), winchDirection, True)

    def moveCableDistance(self, winchDirection):
        """

        Move the actuator one cable width
        :param winchDirection: direction of ROV winch, 1 is forward and -1 is backward
        :return:
        """
        print("moving actuator........")
        self.move(const.Actuator.cableDiameter, winchDirection, False)

    def checkReadSwitch(self, direction):

        if (self.readSwitchMax.value and direction == 1) or (
                self.readSwitchMin.value and direction == 0):

            self.lastReadTime = time.time()
            # print("Min: " + str(self.readSwitchMin.value) + "\nMax: " + str(self.readSwitchMax.value))
            if self.readCount > 2 and abs(self.lastReadTime - time.time()) < 1:
                self.readCount = 0
                return True

            self.readCount += 1
            return False

    def debug(self, targetPulses):
        print("Actuator pos: " + str(self.currentPulses))
        print("Wanted pos: " + str(targetPulses))
        print(self.stationary_counter)

    def move(self, distance, winchDirection, manualOverride):  # default to cable diameter
        """
        :param winchDirection:
        :param distance: inches
        :param manualOverride:
        """
        self.currentPulses = 0  # zero position tracker
        targetPulses = util.inchesToPulses(distance)

        # calculations for direction
        speed, direction = util.calculateActuatorState(distance, winchDirection, self.currentForwardDirection, manualOverride)

        self.setSpeed(speed)  # write a speed
        self.setDirection(direction)

        self.stationary_counter = 0

        while abs(self.currentPulses) <= abs(targetPulses):

            if self.activeSpeed == 0:
                print("Winch control loop overwritten")
                break

            if self.stationary_counter > 1000:
                print("stationary limit reached")
                break

            if self.checkReadSwitch(direction):
                print("reed switch triggered")

                print("Pre-Direction: " + str(self.currentForwardDirection))
                if not manualOverride:
                    self.changeDirection()
                print("Post-Direction: " + str(self.currentForwardDirection))
                break

            time.sleep(const.ROVconst.actuatorMoveSleep)

        self.setSpeed(0)
