# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" A dummy filter plugin to tests iprpc module in Fledge. """


import logging
import os

import filter_ingest
from fledge.common import logger, iprpc
from fledge.plugins.common import utils

__author__ = "Deepanshu Yadav"
__copyright__ = "Copyright (c) 2020 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_DEFAULT_CONFIG = {
    'plugin': {  # mandatory
        'description': 'Filter plugin to calculate rms value from south service using numpy',
        'type': 'string',
        'default': 'numpy_iprpc_filter',
        'readonly': 'true'
    },
    'enable': {  # mandatory
        'description': 'Enable / disable this plugin',
        'type': 'boolean',
        'default': 'False',
        'displayName': 'Enable this plugin',
        'order': '1'
    },
    'assetName': {
        'description': 'Asset name from which rms values to be calculated.',
        'type': 'string',
        'default': 'numpy_ingest',
        'displayName': 'Asset Name',
        'order': '2'
    },
    'dataPointName': {
        'description': 'The data point name from asset',
        'type': 'string',
        'default': 'random',
        'displayName': 'Data Point Name',
        'order': '3'
    },
    'numSamples': {
        'description': 'Number of samples to collect before applying rms function',
        'type': 'string',
        'default': '100',
        'displayName': 'Num Of Samples',
        'order': '4'
    }
}

_LOGGER = logger.setup(__name__, level=logging.INFO)
_module_dir = os.path.dirname(__file__)

shutdown_in_progress = False
the_rpc = None


def plugin_info():
    """ Returns information about the plugin.
    Args:
    Returns:
        dict: plugin information
    Raises:
    """
    _LOGGER.info("plugin_info called")
    return {
        'name': 'numpy_filter',
        'version': '1.8.2',
        'mode': 'none',
        'type': 'filter',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(config, ingest_ref, callback):
    """ Initialise the plugin.
    Args:
        config: JSON configuration document for the plugin configuration category
    Returns:
        data: JSON object to be used in future calls to the plugin
    Raises:
    """
    global shutdown_in_progress, the_rpc
    _LOGGER.info("plugin_init called")
    _config = config  # copy.deepcopy(config)
    _config['ingest_ref'] = ingest_ref
    _config['callback'] = callback

    # start a server for the ai algorithm the user has configured
    the_rpc = iprpc.IPCModuleClient("np_server", _module_dir)

    _config['readings_buffer'] = list()
    shutdown_in_progress = False
    return _config


def plugin_ingest(handle, data):
    """ plugin_ingest -- calculate rms values usinfg numpy """

    global shutdown_in_progress

    if shutdown_in_progress:
        return

    if not handle['enable']['value']:
        # Filter not enabled, just pass data onwards
        filter_ingest.filter_ingest_callback(handle['callback'], handle['ingest_ref'], data)
        return

    _asset_name = handle['assetName']['value']
    _datapoint_name = handle['dataPointName']['value']
    _num_samples_for_calculation = int(handle['numSamples']['value'])

    if type(data) == dict:
        data = [data]

    if len(data) == 0:
        _LOGGER.info("empty data received ")

    buffer = []
    handle['readings_buffer'].extend(data)

    if len(handle['readings_buffer']) < _num_samples_for_calculation:
        return

    for reading in handle['readings_buffer'][:_num_samples_for_calculation]:
        if reading['asset'] != _asset_name:
            continue

        datapoints = reading['readings']
        if _datapoint_name not in datapoints:
            continue

        single_reading = datapoints[_datapoint_name]
        buffer.append(single_reading)

    rms_value = the_rpc.rms(buffer)

    time_stamp = utils.local_timestamp()
    rms_reading = {'asset': _asset_name + '_RMS', 'timestamp': time_stamp, 'readings': {}}
    rms_reading['readings'][_datapoint_name] = rms_value

    readings_buffer_to_fwd = handle['readings_buffer'][:_num_samples_for_calculation]

    readings_buffer_to_fwd.append(rms_reading)

    filter_ingest.filter_ingest_callback(handle['callback'], handle['ingest_ref'], readings_buffer_to_fwd)

    handle['readings_buffer'] = handle['readings_buffer'][_num_samples_for_calculation:]


def plugin_reconfigure(handle, new_config):
    """ Reconfigures the plugin
    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    """
    _LOGGER.info("Old config for numpy filter plugin={} \n new config={}".format(handle.config, new_config))
    plugin_shutdown(handle)
    new_handle = plugin_init(new_config)
    return new_handle


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup
    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        plugin shutdown
    """
    _LOGGER.info("Plugin shutdown ")
    global shutdown_in_progress, the_rpc
    shutdown_in_progress = True
    if the_rpc is not None:
        try:
            the_rpc.plugin_shutdown()
        except EOFError:
            _LOGGER.info("Normal shutdown exit")
        the_rpc = None
