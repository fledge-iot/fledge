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
    """Storage client async"""

    foglamp_svc_name = None
    """FogLAMP service name"""

    _registered_asset_records = None
    """Set of rows for asset_tracker already in the storage tables"""

    def __init__(self, storage=None):
        if self._storage is None:
            if not isinstance(storage, StorageClientAsync):
                raise TypeError('Must be a valid Async Storage object')
            self._storage = storage
            self.foglamp_svc_name = ''

    async def load_asset_records(self):
        """ Fetch all asset_tracker records from database """

        self._registered_asset_records = []
        try:
            payload = PayloadBuilder().SELECT("asset", "event", "service", "plugin").payload()
            results = await self._storage.query_tbl_with_payload('asset_tracker', payload)
            for row in results['rows']:
                self._registered_asset_records.append(row)
        except Exception as ex:
            _logger.exception('Failed to retrieve asset records, %s', str(ex))

    async def add_asset_record(self, *,  asset, event, service, plugin):
        """
        Args:
             asset: asset code of the record
             event: event the record is recording, one of a set of possible events including Ingest, Egress, Filter
             service: The name of the service that made the entry
             plugin: The name of the plugin, that has been loaded by the service.
        """
        # If (asset + event + service + plugin) row combination exists in _find_registered_asset_record then return
        d = {"asset": asset, "event": event, "service": service, "plugin": plugin}
        if d in self._registered_asset_records:
            return

        # The name of the FogLAMP this entry has come from.
        # This is defined as the service name and configured as part of the general configuration of FogLAMP.
        # it will only change on restart! Later we may want to fix it via callback mechanism
        if len(self.foglamp_svc_name) == 0:
            cfg_manager = ConfigurationManager(self._storage)
            svc_config = await cfg_manager.get_category_item(category_name='service', item_name='name')
            self.foglamp_svc_name = svc_config['value']

        try:
            payload = PayloadBuilder().INSERT(asset=asset, event=event, service=service, plugin=plugin, foglamp=self.foglamp_svc_name).payload()
            result = await self._storage.insert_into_tbl('asset_tracker', payload)
            response = result['response']
            d = {"asset": asset, "event": event, "service": service, "plugin": plugin}
            self._registered_asset_records.append(d)
        except KeyError:
            raise ValueError(result['message'])
        except StorageServerError as ex:
            err_response = ex.error
            raise ValueError(err_response)
        else:
            return True
