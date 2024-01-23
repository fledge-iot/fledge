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
    urgency = {"Critical": 1, "High": 2, "Normal": 3, "Low": 4}

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
            storage_result = await self.storage_client.query_tbl_with_payload('alerts', q_payload)
            result = []
            if 'rows' in storage_result:
                for row in storage_result['rows']:
                    tmp = {"key": row['key'],
                             "message": row['message'],
                             "urgency": self._urgency_name_by_value(row['urgency']),
                             "timestamp": row['timestamp']
                             }
                    result.append(tmp)
            self.alerts = result
        except Exception as ex:
            raise Exception(ex)
        else:
            return self.alerts

    async def get_by_key(self, name):
        """ Get an alert by key """
        key_found = [a for a in self.alerts if a['key'] == name]
        if key_found:
            return key_found[0]
        try:
            q_payload = PayloadBuilder().SELECT("key", "message", "urgency", "ts").ALIAS(
                "return", ("ts", 'timestamp')).FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")).WHERE(
                ["key", "=", name]).payload()
            results = await self.storage_client.query_tbl_with_payload('alerts', q_payload)
            alert = {}
            if 'rows' in results:
                if len(results['rows']) > 0:
                    row = results['rows'][0]
                    alert = {"key": row['key'],
                           "message": row['message'],
                           "urgency": self._urgency_name_by_value(row['urgency']),
                           "timestamp": row['timestamp']
                           }
            if not alert:
                raise KeyError('{} alert not found.'.format(name))
        except KeyError as err:
            msg = str(err.args[0])
            raise KeyError(msg)
        else:
            return alert

    async def add(self, params):
        """ Add an alert """
        response = None
        try:
            payload = PayloadBuilder().INSERT(**params).payload()
            insert_api_result = await self.storage_client.insert_into_tbl('alerts', payload)
            if insert_api_result['response'] == 'inserted' and insert_api_result['rows_affected'] == 1:
                response = {"alert": params}
                self.alerts.append(params)
        except Exception as ex:
            raise Exception(ex)
        else:
            return response

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

    def _urgency_name_by_value(self, value):
        try:
            name = list(self.urgency.keys())[list(self.urgency.values()).index(value)]
        except:
            name = "UNKNOWN"
        return name

