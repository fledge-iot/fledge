"""
FogLAMP filtering for readings data
using Python 3.5
"""

__author__ = "Yash Tatkondawar"
__copyright__ = "Copyright (c) 2019 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import sys
import json

"""
Filter configuration set by set_filter_config(config)
"""

"""
filter_config, global variable
"""
filter_config = dict()

"""
Set the Filter configuration into filter_config (global variable)

Input data is a dict with 'config' key and JSON string version wit data

JSON string is loaded into a dict, set to global variable filter_config

Return True
"""
def set_filter_config(configuration):
    print(configuration)
    global filter_config
    filter_config = json.loads(configuration['config'])

    return True

"""
Method for filtering readings data

Input is array of dicts
[
    {'reading': {'power_set1': '5980'}, 'asset_code': 'lab1'},
    {'reading': {'power_set1': '211'}, 'asset_code': 'lab1'}
]

Input data:
   readings: can be modified, dropped etc
Output is array of dict
"""
def readings35(readings):
    # Get list of asset code to filter
    if ('asset_code' in filter_config):
        asset_codes = filter_config['asset_code']
    else:
        asset_codes = []

    for elem in readings:
            print("IN=" + str(elem))
            reading = elem['reading']
            # Apply some changes: multiply by 2 and divide by 10 to all datapoint values
            for key in reading:
                newVal = (reading[key] * 2)/10
                reading[key] = newVal

            print("OUT=" + str(elem))
    return readings
