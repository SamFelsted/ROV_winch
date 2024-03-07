class ROVconst:
    # Controls for the multithreading speeds
    failureSleep = 10
    getCommandSleep = 0.1
    controlSleep = 0.1
    rotationReedSwitchSleep = 0.001
    motorCurrentSleep = 0.1
    actuatorMoveSleep = 0.05


class Motor:
    class Pins:
        FWD0_REV1_pin = 26
        ON_OFF_pin = 19
        mot_pot_pin = 16
        rotation_pin = 24
        current_limit = 15
        overBoardingPin = 0

    RETRACT = 1
    EXTEND = 0

    readSwitchDelay = 0.250
    readSwitchThreshold = 2  # number of ticks until a read, smaller is more sensitive

    voltageDivider = (100 + 47) / 100
    currentLimit = 15


class Actuator:
    class Pins:
        ONOFFPin = 20
        directionPin = 21
        feedbackPin = 10

        readSwitchMin = 7
        readSwitchMax = 8

    class SetPoints:
        minPulseTicks = 0
        maxPulseTicks = 360  # found empirically

    RETRACT = 1
    EXTEND = 0
    false_pulse_delay_actuator = 0  # (zero for no debounce delay)
    pulses_per_inch = (25.4 * 17.4)  # 17.4 pulses for mm, divided by magic number found empirically
    cableDiameter = 0.3  # TESTING NUMBER PLEASE USE A BETTER ONE

    pGain = 1.75
