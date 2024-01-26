# pyright: reportMissingImports=false
import time
import board
import busio
from digitalio import DigitalInOut, Direction, Pull  # GPIO module
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory
from threading import Thread

import util

factory = PiGPIOFactory()
false_pulse_delay_reed_sw = 0.250


class Motor:

    def __init__(
            self,
            FWD0_REV1_pin,
            ON_OFF_pin,
            mot_pot_pin,
            rotation_pin,
            currentLimit
    ):

        self.FWD0_REV1 = DigitalInOut(eval('board.D' + str(FWD0_REV1_pin)))
        self.FWD0_REV1.direction = Direction.OUTPUT

        self.ON = DigitalInOut(eval('board.D' + str(ON_OFF_pin)))
        self.ON.direction = Direction.OUTPUT
        self.ON.value = 0

        self.servo = AngularServo(mot_pot_pin, min_angle=0, max_angle=270, min_pulse_width=0.0005,
                                  max_pulse_width=0.0025)
        self.servo.angle = 0

        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.current_sensor = ADS.ADS1115(self.i2c, address=0x48)
        self.current_limit = currentLimit

        # rotation tracking for spool
        self.reed_sw = DigitalInOut(eval('board.D' + str(rotation_pin)))
        self.reed_sw.direction = Direction.INPUT
        self.reed_sw.pull = Pull.DOWN
        self.last_reed_time = time.time() - false_pulse_delay_reed_sw
        self.NeedToMoveActuator = False
        self.RotationCounter = 0

    def set(self, speed, direction):

        if direction == 0:  # off
            self.off()
            return

        elif direction == 1:  # and encoder_position < max_line_out: # FWD (feed out line)
            self.FWD0_REV1.value = 0
        elif direction == -1:  # REV (take in line)
            self.FWD0_REV1.value = 1

        print("Motor speed set")
        self.servo.angle = util.clamp(speed, 0, 100) * 270 / 100
        self.ON.value = 1

    def off(self):
        print("motor off")
        self.ON.value = 0
        self.servo.angle = 0

    # reed switch for rotation tracking     
    def rotationTrackingReedSw(self):
        prior_reedsw_value = self.reed_sw.value
        while True:
            current_reedsw_value = self.reed_sw.value
            if current_reedsw_value == 1 and prior_reedsw_value == 0:
                current_reed_time = time.time()
                if (current_reed_time - self.last_reed_time) > false_pulse_delay_reed_sw:
                    if self.reed_sw.value == 1:
                        self.last_reed_time = current_reed_time
                        self.NeedToMoveActuator = True  # move actuator one cable width
                        self.RotationCounter = self.RotationCounter + 1
            prior_reedsw_value = current_reedsw_value

    def countRotations(self):
        self.rotations = 0
        prior_count = self.RotationCounter
        while True:
            curr_count = self.RotationCounter
            if curr_count > prior_count:
                if self.FWD0_REV1.value == 0:  # feeding line out
                    self.rotations = self.rotations + 1
                elif self.FWD0_REV1.value == 1:  # taking line in
                    self.rotations = self.rotations - 1
                prior_count = curr_count
            time.sleep(0.1)

    def monitorCurrent(self):
        # Measure current draw of motor. Shut off if above threshold
        voltage_divider = (100 + 47) / 100

        while True:
            if self.ON.value == 1:
                ADCread = AnalogIn(self.current_sensor, ADS.P0)
                volty = ADCread.voltage
                curry = (-10 * volty * voltage_divider + 25)
                vs = '%.2f' % volty
                cs = '%.2f' % curry
                # print(vs, "V ; ", cs, "A")

                if abs(curry) > self.current_limit:
                    for i in range(4):  # double check before shutoff -- take an average over 50 ms
                        time.sleep(0.01)
                        ADCread = AnalogIn(self.current_sensor, ADS.P0)
                        volty = ADCread.voltage
                        curry = curry - 10 * volty * voltage_divider + 25
                    curry = curry / (i + 2)
                    if abs(curry) > self.current_limit:
                        self.ON.value = 0
                        self.set(0)
                        print("HIGH CURRENT (", str(curry), "A ) DETECTED! shutting off motor...")
