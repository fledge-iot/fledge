# -*- coding: utf-8 -*-


""" Generate exponential moving average
"""
import json

rate = 0.07  # rate default value: include 7% of current value (and 93% of history)
latest = None  # latest ema value


def set_filter_config(configuration):
    """ Set configuration if provided

    :param configuration:
    :return:
    """
    global rate
    config = json.loads(configuration['config'])
    if'rate' in config:
        rate = config['rate']
    return True


def doit(reading):
    """ Process a reading

    :param reading:
    :return:
    """
    global rate, latest
    for attribute in list(reading):
        if not latest:
            latest = reading[attribute]
        latest = reading[attribute] * rate + latest * (1 - rate)
        reading[b'ema'] = latest


def ema(readings):
    """ Process one or more readings

    :param readings:
    :return:
    """
    for elem in list(readings):
        doit(elem['reading'])
    return readings
