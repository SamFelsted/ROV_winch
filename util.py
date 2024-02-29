"""
    Purpose: Static functions that may be used for simplifying code
    Author: Sam Felsted
"""
import const


def flipBit(bit):
    """
    Turns a 1 into a 0 and vice versa
    :param bit: (0, 1)
    :return: (1, 0) opposite of input
    """
    return int((not bool(bit)))


def clamp(x, low, high):
    """
    Cuts input lower or higher than max or min
    :param x:
    :param low: the lowest possible input
    :param high: the highest possible input
    :return: input within range
    """
    return max(min(x, high), low)


def calculateActuatorState(distance, winchDirection, forwardDirection, manualOverride):
    """
    Calculates the speed of the actuator based on the speed of the winch
    :param winchDirection:
    :param distance: inches
    :param forwardDirection:
    :return: speed, direction
    """
    if manualOverride:
        speed = 1
        direction = 0 if distance > 0 else 1
    else:
        speed = clamp(abs(distance * const.Actuator.pGain), 0, 1)
        direction = flipBit(forwardDirection) if distance < 0 else forwardDirection

        if winchDirection == -1:
            direction = flipBit(direction)

    return speed, direction


def inchesToPulses(inches):
    """
    :param inches: self-explanatory
    :return: pulses
    """
    return round(const.Actuator.pulses_per_inch * inches)
