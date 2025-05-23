# pyright: reportMissingImports=false
import time
import board
import busio
from digitalio import DigitalInOut, Direction, Pull  # GPIO module
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory
from PWMController import PWMController

import const
import util

factory = PiGPIOFactory()


class Motor:

    def __init__(
            self,
            FWD0_REV1_pin,
            ON_OFF_pin,
            mot_pot_pin,
            rotation_pin,
            currentLimit
    ):
        
        self.PWMController = PWMController(
            pwmFrequency = const.Motor.pwmFrequency,
            pwmPinID = const.Motor.Pins.pwmPin,
            pwmDutyCycle = 0
        )

        self.FWD0_REV1 = DigitalInOut(eval('board.D' + str(FWD0_REV1_pin)))
        self.FWD0_REV1.direction = Direction.OUTPUT

        self.ON = DigitalInOut(eval('board.D' + str(ON_OFF_pin)))
        self.ON.direction = Direction.OUTPUT
        self.ON.value = 0

        # self.servo = AngularServo(mot_pot_pin, min_angle=0, max_angle=270, min_pulse_width=0.0005,
        #                           max_pulse_width=0.0025)
        # self.servo.angle = 0

        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.current_sensor = ADS.ADS1115(self.i2c, address=0x48)
        self.current_limit = currentLimit

        self.direction = 0

        # rotation tracking for spool
        self.readSwitch = DigitalInOut(eval('board.D' + str(rotation_pin)))
        self.readSwitch.direction = Direction.INPUT
        self.readSwitch.pull = Pull.DOWN
        self.last_reed_time = time.time() - const.Motor.readSwitchDelay
        self.NeedToMoveActuator = False
        self.rotationCounter = 0

        # Logged values - TODO add logging
        self.motorVoltage = 0
        self.motorCurrent = 0

        # over-boarding placeholder code
        # self.topSwitch = DigitalInOut(eval('board.D' + str(overBoarding)))
        # self.topSwitch.direction = Direction.INPUT
        # self.topSwitch.pull = Pull.DOWN

    def getDirection(self):
        return self.direction

    def set(self, speed, direction):

        if direction == 0:  # off
            self.off()
            return

        elif direction == 1:  # and encoder_position < max_line_out: # FWD (feed out line)
            self.FWD0_REV1.value = 0
            print("Forward")
        elif direction == -1:  # REV (take in line)
            print("Reverse")
            self.FWD0_REV1.value = 1

            self.direction = 0

        print("Motor speed set")
        # self.servo.angle = util.clamp(speed, 0, 100) * 270 / 100
        self.PWMController.setDuty(int(float(speed) / 100 * 255))
        self.ON.value = 1

    def off(self):
        print("motor off")
        self.ON.value = 0
        # self.servo.angle = 0
        self.PWMController.setDuty(0)
        self.direction = 0

    # reed switch for rotation tracking     
    def rotationReedSwitchTracking(self):
        readCounts = 0
        lastReadTime = time.time()
        while True:
            time.sleep(const.ROVconst.rotationReedSwitchSleep)
            if self.readSwitch.value:
                if (time.time() - lastReadTime) > const.Motor.readSwitchDelay and self.ON.value == 1:  # check time
                    # since last read
                    readCounts += 1
                    if readCounts >= const.Motor.readSwitchThreshold:
                        self.NeedToMoveActuator = True
                        if self.direction == 1:
                            self.rotationCounter += 1
                        elif self.direction == -1:
                            self.rotationCounter += -1
                        readCounts = 0
                        lastReadTime = time.time()

            else:
                readCounts = 0

    def readVoltageAndCurrent(self):
        ADCRead = AnalogIn(self.current_sensor, ADS.P0)
        motorVoltage = ADCRead.voltage
        motorCurrent = (-10 * self.motorVoltage * const.Motor.voltageDivider + 25)
        return motorVoltage, motorCurrent

    def monitorCurrent(self):
        """
        Monitors the current of the motor, shuts off motor if above threshold in const
        """
        while True:
            time.sleep(const.ROVconst.motorCurrentSleep)
            if self.ON.value == 1:

                self.motorVoltage, self.motorCurrent = self.readVoltageAndCurrent()

                # vs = '%.2f' % self.motorVoltage
                # cs = '%.2f' % self.motorCurrent
                # print(vs, "V ; ", cs, "A")

                if abs(self.motorCurrent) > self.current_limit:
                    avgCurrent = self.motorCurrent
                    for i in range(4):  # double check before shutoff -- take an average over 50 ms
                        time.sleep(0.01)
                        voltage, current = self.readVoltageAndCurrent()
                        avgCurrent = (avgCurrent + current) / 2

                    if abs(avgCurrent) > self.current_limit:
                        self.off()
                        print("HIGH CURRENT (", str(self.motorCurrent), "A ) DETECTED! shutting off motor...")
