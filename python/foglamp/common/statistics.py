# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from foglamp.common import logger

from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.storage_client import StorageClient


__author__ = "Ashwin Gopalakrishnan, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__)


class Statistics(object):
    """ Statistics interface of the API to gather the available statistics counters,
        calculate the deltas from the previous run of the process and write the deltas
        to a statistics record.
    """

    def __init__(self, storage):
        if not isinstance(storage, StorageClient):
            raise TypeError('Must be a valid Storage object')

        self._storage = storage

    async def update(self, key, value_increment):
        """ UPDATE the value column only of a statistics row based on key

        Args:
            key: statistics key value (required)
            value_increment: amount to increment the value by

        Returns:
            None
        """
        try:
            payload = PayloadBuilder()\
                .WHERE(["key", "=", key])\
                .EXPR(["value", "+", value_increment])\
                .payload()
            self._storage.update_tbl("statistics", payload)
        except:
            _logger.exception(
                'Unable to update statistics value based on statistics_key %s and value_increment %s'
                , key, value_increment)
            raise

    async def add_update(self, sensor_stat_dict):
        """UPDATE the value column of a statistics based on key, if key is not present, ADD the new key

        Args:
            sensor_stat_dict: Dictionary containing the key value of Asset name and value increment

        Returns:
            None
        """
        for key, value_increment in sensor_stat_dict.items():
            # Try updating the statistics value for given key
            try:
                payload = PayloadBuilder() \
                    .WHERE(["key", "=", key]) \
                    .EXPR(["value", "+", value_increment]) \
                    .payload()
                result = self._storage.update_tbl("statistics", payload)
                if result["response"] != "updated":
                    raise KeyError
            # If key was not present, add the key and with value = value_increment
            except KeyError:
                desc_txt = "The number of readings received by FogLAMP since startup for sensor {}".format(key)
                payload = PayloadBuilder().INSERT(key=key, description=desc_txt,
                                                  value=value_increment, previous_value=0).payload()
                self._storage.insert_into_tbl("statistics", payload)
            except Exception as ex:
                _logger.exception(
                    'Unable to update statistics value based on statistics_key %s and value_increment %s, error %s'
                    , key, value_increment, str(ex))
                raise

# TODO: FOGL-484 Move below commented code to tests directory
# async def _main():
#     _storage = StorageClient(core_management_host="0.0.0.0", core_management_port=33881)
#
#     _stats = Statistics(_storage)
#     await _stats.update(key='READINGS', value_increment=10)
#
#
# if __name__ == '__main__':
#     import asyncio
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(_main())
