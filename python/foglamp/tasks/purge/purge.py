# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END
"""
Purge readings based on the age of the readings.

Readings data that is older than the specified age will be removed from the readings store.

Conditions:
    1. If the configuration value of retainUnsent is set to True then any reading with an id value that is
    greater than the minimum(last_object) of streams table will not be removed.

    2. If the configuration value of retainUnsent is set to False then all readings older than the configured age | size,
    regardless of the minimum(last_object) of streams table will be removed.

Statistics reported by Purge process are:
    -> Readings removed
    -> Unsent readings removed
    -> Readings retained (based on retainUnsent configuration)
    -> Remaining readings
    All these statistics are inserted into the log table
"""
import asyncio
import time

from foglamp.common.audit_logger import AuditLogger
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common import statistics
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common import logger
from foglamp.common.storage_client.exceptions import *
from foglamp.common.process import FoglampProcess


__author__ = "Ori Shadmon, Vaibhav Singhal, Mark Riddoch, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class Purge(FoglampProcess):

    _DEFAULT_PURGE_CONFIG = {
        "age": {
            "description": "Age of data to be retained (in hours). All data older than this value will be removed," +
                           "unless retained.",
            "type": "integer",
            "default": "72"
        },
        "size": {
            "description": "Maximum size of data to be retained (in Kbytes). Oldest data will be removed to keep "
                           "below this size, unless retained.",
            "type": "integer",
            "default": "1000000"
        },
        "retainUnsent": {
            "description": "Retain data that has not been sent to any historian yet.",
            "type": "boolean",
            "default": "False"
        }
    }
    _CONFIG_CATEGORY_NAME = 'PURGE_READ'
    _CONFIG_CATEGORY_DESCRIPTION = 'Purge the readings table'

    def __init__(self):
        super().__init__()
        self._logger = logger.setup("Data Purge")
        self._audit = AuditLogger(self._storage_async)

    async def write_statistics(self, total_purged, unsent_purged):
        stats = await statistics.create_statistics(self._storage_async)
        await stats.update('PURGED', total_purged)
        await stats.update('UNSNPURGED', unsent_purged)

    async def set_configuration(self):
        """" set the default configuration for purge
        :return:
            Configuration information that was set for purge process
        """
        cfg_manager = ConfigurationManager(self._readings_storage_async)
        await cfg_manager.create_category(self._CONFIG_CATEGORY_NAME,
                                          self._DEFAULT_PURGE_CONFIG,
                                          self._CONFIG_CATEGORY_DESCRIPTION)

        # Create the child category for purge
        try:
            await cfg_manager.create_child_category("Utilities", [self._CONFIG_CATEGORY_NAME])
        except KeyError:
            self._logger.error("Failed to create child category for purge process")
            raise

        return await cfg_manager.get_category_all_items(self._CONFIG_CATEGORY_NAME)

    async def purge_data(self, config):
        """" Purge readings table based on the set configuration
        :return:
            total rows removed
            rows removed that were not sent to any historian
        """
        total_rows_removed = 0
        unsent_rows_removed = 0
        unsent_retained = 0
        start_time = time.strftime('%Y-%m-%d %H:%M:%S.%s', time.localtime(time.time()))

        payload = PayloadBuilder().AGGREGATE(["count", "*"]).payload()
        result = await self._storage_async.query_tbl_with_payload("readings", payload)
        total_count = result['rows'][0]['count_*']

        payload = PayloadBuilder().AGGREGATE(["min", "last_object"]).payload()
        result = await self._storage_async.query_tbl_with_payload("streams", payload)
        last_id = result["rows"][0]["min_last_object"] if result["count"] == 1 else 0

        flag = "purge" if config['retainUnsent']['value'] == "False" else "retain"
        try:
            if int(config['age']['value']) != 0:

                result = await self._readings_storage_async.purge(age=config['age']['value'], sent_id=last_id, flag=flag)

                total_count = result['readings']
                total_rows_removed = result['removed']
                unsent_rows_removed = result['unsentPurged']
                unsent_retained = result['unsentRetained']
        except ValueError:
            self._logger.error("Configuration item age {} should be integer!".format(config['age']['value']))

        except StorageServerError as ex:
            # skip logging as its already done in details for this operation in case of error
            # FIXME: check if ex.error jdoc has retryable True then retry the operation else move on
            pass

        try:
            if int(config['size']['value']) != 0:
                result = await self._readings_storage_async.purge(size=config['size']['value'], sent_id=last_id, flag=flag)

                total_count += result['readings']
                total_rows_removed += result['removed']
                unsent_rows_removed += result['unsentPurged']
                unsent_retained += result['unsentRetained']
        except ValueError:
            self._logger.error("Configuration item size {} should be integer!".format(config['size']['value']))

        except StorageServerError as ex:
            # skip logging as its already done in details for this operation in case of error
            # FIXME: check if ex.error jdoc has retryable True then retry the operation else move on
            pass

        end_time = time.strftime('%Y-%m-%d %H:%M:%S.%s', time.localtime(time.time()))

        if total_rows_removed > 0:
            """ Only write an audit log entry when rows are removed """
            await self._audit.information('PURGE', {"start_time": start_time,
                                                    "end_time": end_time,
                                                    "rowsRemoved": total_rows_removed,
                                                    "unsentRowsRemoved": unsent_rows_removed,
                                                    "rowsRetained": unsent_retained,
                                                    "rowsRemaining": total_count
                                                    })
        else:
            self._logger.info("No rows purged")

        return total_rows_removed, unsent_rows_removed

    async def run(self):
        """" Starts the purge task

            1. Write and read Purge task configuration
            2. Purge as per the configuration
            3. Collect statistics
            4. Write statistics to statistics table
        """
        try:
            config = await self.set_configuration()
            total_purged, unsent_purged = await self.purge_data(config)
            await self.write_statistics(total_purged, unsent_purged)
        except Exception as ex:
            self._logger.exception(str(ex))
