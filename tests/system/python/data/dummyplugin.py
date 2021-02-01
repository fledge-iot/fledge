# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Async Plugin used for testing purpose """
import asyncio
import copy
import uuid
import logging
import async_ingest

from fledge.common import logger
from fledge.services.south import exceptions
from threading import Thread
from datetime import datetime, timezone, timedelta

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

c_callback = None
c_ingest_ref = None
loop = None
_task = None
t = None

_DEFAULT_CONFIG = {
    'plugin': {
        'description': 'Test Async Plugin',
        'type': 'string',
        'default': 'dummyplugin',
        'readonly': 'true'
    },
    'assetPrefix': {
        'description': 'Prefix of asset name',
        'type': 'string',
        'default': 'test-',
        'order': '1',
        'displayName': 'Asset Name Prefix'
    },
    'loudnessAssetName': {
        'description': 'Loudness sensor asset name',
        'type': 'string',
        'default': 'loudness',
        'order': '3',
        'displayName': 'Loudness Sensor Asset Name'
    }
}

_LOGGER = logger.setup(__name__, level=logging.INFO)


def plugin_info():
    """ Returns information about the plugin.
    Args:
    Returns:
        dict: plugin information
    Raises:
    """
    return {
        'name': 'TEST Async Plugin',
        'version': '2.0.0',
        'mode': 'async',
        'type': 'south',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(config):
    """ Initialise the plugin.
    Args:
        config: JSON configuration document for the South plugin configuration category
    Returns:
        data: JSON object to be used in future calls to the plugin
    Raises:
    """
    handle = copy.deepcopy(config)
    return handle


def plugin_start(handle):
    """ Extracts data from the sensor and returns it in a JSON document as a Python dict.
    Available for async mode only.
    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        returns a sensor reading in a JSON document, as a Python dict, if it is available
        None - If no reading is available
    Raises:
        TimeoutError
    """
    global _task, loop, t
    loop = asyncio.new_event_loop()
    _task = asyncio.ensure_future(_start_aiotest(handle), loop=loop)

    def run():
        global loop
        loop.run_forever()

    t = Thread(target=run)
    t.start()


async def _start_aiotest(handle):
    # This plugin adds 6 data points 2 within same min, 2 within same hour and 2 within same day
    # this data is useful when testing asset browsing based on timestamps
    ts_lst = list()
    ts_lst.append(str(datetime.now(timezone.utc).astimezone()))
    ts_lst.append(str(datetime.now(timezone.utc).astimezone() - timedelta(seconds=3)))
    ts_lst.append(str(datetime.now(timezone.utc).astimezone() - timedelta(minutes=5)))
    ts_lst.append(str(datetime.now(timezone.utc).astimezone() - timedelta(minutes=6)))
    ts_lst.append(str(datetime.now(timezone.utc).astimezone() - timedelta(hours=3)))
    ts_lst.append(str(datetime.now(timezone.utc).astimezone() - timedelta(hours=5)))

    i = 1
    for user_ts in ts_lst:
        try:
            data = list()
            data.append({
                'asset': '{}{}'.format(handle['assetPrefix']['value'], handle['loudnessAssetName']['value']),
                'timestamp': user_ts,
                'key': str(uuid.uuid4()),
                'readings': {"loudness": i}
            })
            async_ingest.ingest_callback(c_callback, c_ingest_ref, data)
            await asyncio.sleep(0.1)

        except (Exception, RuntimeError) as ex:
            _LOGGER.exception("TEST exception: {}".format(str(ex)))
            raise exceptions.DataRetrievalError(ex)
        else:
            i += 1


def plugin_register_ingest(handle, callback, ingest_ref):
    """Required plugin interface component to communicate to South C server

    Args:
        handle: handle returned by the plugin initialisation call
        callback: C opaque object required to passed back to C->ingest method
        ingest_ref: C opaque object required to passed back to C->ingest method
    """
    global c_callback, c_ingest_ref
    c_callback = callback
    c_ingest_ref = ingest_ref


def plugin_reconfigure(handle, new_config):
    """ Reconfigures the plugin

    Args:
        handle: handle returned by the plugin initialisation call
        new_config: JSON object representing the new configuration category for the category
    Returns:
        new_handle: new handle to be used in the future calls
    """
    _LOGGER.info("Old config for TEST plugin {} \n new config {}".format(handle, new_config))
    new_handle = copy.deepcopy(new_config)
    return new_handle


def plugin_shutdown(handle):
    """ Shutdowns the plugin doing required cleanup, to be called prior to the South plugin service being shut down.

    Args:
        handle: handle returned by the plugin initialisation call
    Returns:
        plugin shutdown
    """
    _LOGGER.info('TEST plugin shut down.')

