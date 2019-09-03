# generate exponential moving average

# rate default value: include 7% of current value (and 93% of history)
rate = 0.07

# latest ema value
latest = None

import json
# get configuration if provided.
# set this JSON string in configuration:
#      {"rate":0.07}
def set_filter_config(configuration):
    global rate
    config = json.loads(configuration['config'])
    if('rate' in config):
        rate = config['rate']
    return True

# Process a reading
def doit(reading):
    global rate, latest
    for attribute in list(reading):
        if not latest:
            latest = reading[attribute]
        latest = reading[attribute] * rate + latest * (1 - rate)
        reading[b'ema'] = latest

# process one or more readings
def ema(readings):
    for elem in list(readings):
        doit(elem['reading'])
    return readings
