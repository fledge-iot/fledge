# add reading id inside datapoint

import json


def set_filter_config(configuration):
    config = json.loads(configuration['config'])
    return True


# process one or more readings
def set_id(readings):
    for elem in list(readings):
        id = elem['id']
        reading = elem['reading']
        reading[b'id_datapoint'] = id
    return readings


