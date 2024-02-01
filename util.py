"""
    Purpose: Static functions that may be used for simplifying code
    Author: Sam Felsted
"""
import const


def clamp(x, low, high):
    """
    Cuts input lower or higher than max or min
    :param x:
    :param low: the lowest possible input
    :param high: the highest possible input
    :return: input within range
    """
    return max(min(x, high), low)


def calculateActuatorSpeed(distance):
    """
    Calculates the speed of the actuator based on the speed of the winch
    :param distance: inches
    :return: speed, direction
    """
    speed = clamp(abs(distance * const.Actuator.pGain), 0, 1)
    print(speed)
    direction = const.Actuator.RETRACT if distance < 0 else const.Actuator.EXTEND

    return speed, direction


def inchesToPulses(inches):
    """
    :param inches: self-explanatory
    :return: pulses
    """
    return round(const.Actuator.pulses_per_inch * inches)
