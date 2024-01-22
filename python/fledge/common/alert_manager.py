# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from fledge.common.logger import FLCoreLogger
from fledge.common.storage_client.payload_builder import PayloadBuilder

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2024 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = FLCoreLogger().get_logger(__name__)

class AlertManagerSingleton(object):
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state


class AlertManager(AlertManagerSingleton):
    storage_client = None
    alerts = []

    def __init__(self, storage_client=None):
        AlertManagerSingleton.__init__(self)
        if not storage_client:
            from fledge.services.core import connect
            self.storage_client = connect.get_storage_async()
        else:
            self.storage_client = storage_client

    async def get_all(self):
        """ Get all alerts from storage """
        try:
            q_payload = PayloadBuilder().SELECT("key", "message", "urgency", "ts").ALIAS(
                "return", ("ts", 'timestamp')).FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")).payload()
            results = await self.storage_client.query_tbl_with_payload('alerts', q_payload)
            if 'rows' in results:
                if results['rows']:
                    self.alerts = results['rows']
        except Exception as ex:
            raise Exception(ex)
        else:
            return self.alerts


    async def delete(self, key=None):
        """ Delete an entry from storage """
        try:
            payload = {}
            message = "Nothing to delete."
            key_exists = -1
            if key is not None:
                key_exists = [index for index, item in enumerate(self.alerts) if item['key'] == key]
                if key_exists:
                    payload = PayloadBuilder().WHERE(["key", "=", key]).payload()
                else:
                    raise KeyError
            result = await self.storage_client.delete_from_tbl("alerts", payload)
            if 'rows_affected' in result:
                if result['response'] == "deleted" and result['rows_affected']:
                    if key is None:
                        message = "Delete all alerts."
                        self.alerts = []
                    else:
                        message = "{} alert is deleted.".format(key)
                        if key_exists:
                            del self.alerts[key_exists[0]]
        except KeyError:
            raise KeyError
        except Exception as ex:
            raise Exception(ex)
        else:
            return message