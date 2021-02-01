# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
from fledge.common import logger
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.storage_client import StorageClientAsync


__author__ = "Ashwin Gopalakrishnan, Ashish Jabble, Mark Riddoch, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__)


async def create_statistics(storage=None):
    stat = Statistics(storage)
    await stat._init()
    return stat


class Statistics(object):
    """ Statistics interface of the API to gather the available statistics counters,
        calculate the deltas from the previous run of the process and write the deltas
        to a statistics record.
    """

    _shared_state = {}

    _storage = None

    _registered_keys = None
    """ Set of keys already in the storage tables """

    def __init__(self, storage=None):
        self.__dict__ = self._shared_state
        if self._storage is None:
            if not isinstance(storage, StorageClientAsync):
                raise TypeError('Must be a valid Async Storage object')
            self._storage = storage

    async def _init(self):
        if self._registered_keys is None:
            await self._load_keys()

    async def update_bulk(self, stat_list):
        """ Bulk update statistics table keys and their values

        Args:
            stat_list: dict containing statistics keys and increment values

        Returns:
            None
        """
        if not isinstance(stat_list, dict):
            raise TypeError('stat_list must be a dict')

        try:
            payload = {"updates": []}
            for k, v in stat_list.items():
                payload_item = PayloadBuilder() \
                    .WHERE(["key", "=", k]) \
                    .EXPR(["value", "+", v]) \
                    .payload()
                payload['updates'].append(json.loads(payload_item))
            await self._storage.update_tbl("statistics", json.dumps(payload, sort_keys=False))
        except Exception as ex:
            _logger.exception('Unable to bulk update statistics %s', str(ex))
            raise

    async def update(self, key, value_increment):
        """ UPDATE the value column only of a statistics row based on key

        Args:
            key: statistics key value (required)
            value_increment: amount to increment the value by

        Returns:
            None
        """
        if not isinstance(key, str):
            raise TypeError('key must be a string')

        if not isinstance(value_increment, int):
            raise ValueError('value must be an integer')

        try:
            payload = PayloadBuilder()\
                .WHERE(["key", "=", key])\
                .EXPR(["value", "+", value_increment])\
                .payload()
            await self._storage.update_tbl("statistics", payload)
        except Exception as ex:
            _logger.exception(
                'Unable to update statistics value based on statistics_key %s and value_increment %d, error %s'
                , key, value_increment, str(ex))
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
                result = await self._storage.update_tbl("statistics", payload)
                if result["response"] != "updated":
                    raise KeyError
            # If key was not present, add the key and with value = value_increment
            except KeyError:
                _logger.exception('Statistics key %s has not been registered', key)
                raise
            except Exception as ex:
                _logger.exception(
                    'Unable to update statistics value based on statistics_key %s and value_increment %s, error %s'
                    , key, value_increment, str(ex))
                raise

    async def register(self, key, description):
        if key in self._registered_keys:
            return
        if len(self._registered_keys) == 0:
            await self._load_keys()
        try:
            payload = PayloadBuilder().INSERT(key=key, description=description, value=0, previous_value=0).payload()
            await self._storage.insert_into_tbl("statistics", payload)
            self._registered_keys.append(key)
        except Exception as ex:
            """ The error may be because the key has been created in another process, reload keys """
            await self._load_keys()
            if key not in self._registered_keys:
                _logger.exception('Unable to create new statistic %s, error %s', key, str(ex))
                raise

    async def _load_keys(self):
        self._registered_keys = []
        try:
            payload = PayloadBuilder().SELECT("key").payload()
            results = await self._storage.query_tbl_with_payload('statistics', payload)
            for row in results['rows']:
                self._registered_keys.append(row['key'])
        except Exception as ex:
            _logger.exception('Failed to retrieve statistics keys, %s', str(ex))
