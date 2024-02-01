class Motor:
    class Pins:
        FWD0_REV1_pin = 26
        ON_OFF_pin = 19
        mot_pot_pin = 16
        rotation_pin = 24
        current_limit = 15

    RETRACT = 1
    EXTEND = 0

    readSwitchDelay = 0.250

    voltageDivider = (100 + 47) / 100
    currentLimit = 3


class Actuator:
    class Pins:
        ONOFFPin = 20
        directionPin = 21
        feedbackPin = 10

    class SetPoints:
        minPulseTicks = 0
        maxPulseTicks = 100

    RETRACT = 1
    EXTEND = 0
    false_pulse_delay_actuator = 0  # (zero for no debounce delay)
    pulses_per_inch = 25.4 * 17.4  # 17.4 pulses for mm
    cableDiameter = 0.42

    pGain = 1.75
