# -*- coding: utf-8 -*-

""" Predict up/down trend in data which has momentum

"""
import json

# exponential moving average rate default values
# short-term: include 15% of current value in ongoing average (and 85% of history)
rate_short = 0.15
# long-term: include 7% of current value
rate_long = 0.07

# short-term and long-term averages.
ema_short = ema_long = None

# trend of data: 5: down / 10: up. Start with up.
trend = 10


# get configuration if provided.
# set this JSON string in configuration:
#      {"rate_short":0.15, "rate_long":0.07}
def set_filter_config(configuration):
    global rate_short, rate_long
    filter_config = json.loads(configuration['config'])
    if 'rate_short' in filter_config:
        rate_short = filter_config['rate_short']
    if 'rate_long' in filter_config:
        rate_long = filter_config['rate_long']
    return True


# Process a reading
def doit(reading):
    global rate_short, rate_long        # config
    global ema_short, ema_long, trend   # internal variables

    for attribute in list(reading):
        if not ema_long:
            ema_long = ema_short = reading[attribute]
        else:
            ema_long = reading[attribute] * rate_long + ema_long * (1 - rate_long)
            reading[b'ema_long'] = ema_long
            ema_short = reading[attribute] * rate_short + ema_short * (1 - rate_short)
            reading[b'ema_short'] = ema_short
            if(trend == 10) != (ema_short > ema_long):
                trend = 5 if trend == 10 else 10
            reading[b'trend'] = trend


# process one or more readings
def trendc(readings):
    for elem in list(readings):
        doit(elem['reading'])
    return readings
