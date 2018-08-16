# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from foglamp.common import logger
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.common.storage_client.exceptions import StorageServerError
from foglamp.common.configuration_manager import ConfigurationManager


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__)


class AssetTracker(object):

    _storage = None

    _registered_asset_records = None
    """ Set of row for asset_event already in the storage tables """

    def __init__(self, storage=None):
        if self._storage is None:
            if not isinstance(storage, StorageClientAsync):
                raise TypeError('Must be a valid Async Storage object')
            self._storage = storage

    async def load_asset_records(self):
        self._registered_asset_records = []
        try:
            payload = PayloadBuilder().SELECT("asset", "event", "service", "plugin").payload()
            results = await self._storage.query_tbl_with_payload('asset_tracker', payload)
            for row in results['rows']:
                self._registered_asset_records.append(row)
        except Exception as ex:
            _logger.exception('Failed to retrieve asset event keys, %s', str(ex))

    async def add_asset_record(self, *,  asset, event, service, plugin):
        if self._find_registered_asset_record(asset, event, service, plugin) is True:
            return

        cfg_manager = ConfigurationManager(self._storage)
        config = await cfg_manager.get_category_item(category_name='service', item_name='name')
        try:
            payload = PayloadBuilder().INSERT(asset=asset, event=event, service=service, plugin=plugin, foglamp=config['value']).payload()
            result = await self._storage.insert_into_tbl('asset_tracker', payload)
            response = result['response']
            d = {"asset": asset, "event": event, "service": service, "plugin": plugin}
            self._registered_asset_records.append(d)
        except KeyError:
            raise ValueError(result['message'])
        except StorageServerError as ex:
            err_response = ex.error
            raise ValueError(err_response)

        return True

    def _find_registered_asset_record(self, asset, event, service, plugin):
        d = {"asset": asset, "event": event, "service": service, "plugin": plugin}
        return d in self._registered_asset_records

