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

    2. If the configuration value of retainUnsent is set to False then all readings older than the configured age,
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

from foglamp import configuration_manager
# from foglamp.statistics import Statistics
from foglamp import statistics
from foglamp.storage.payload_builder import PayloadBuilder
from foglamp.storage.storage import Storage, Readings
from foglamp import logger


__author__ = "Ori Shadmon, Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class Purge:

    _DEFAULT_PURGE_CONFIG = {
        "age": {
            "description": "Age of data to be retained, all data that is older than this value will be removed," +
                           "unless retained. (in Hours)",
            "type": "integer",
            "default": "72"
        },
        "retainUnsent": {
            "description": "Retain data that has not been sent to any historian yet.",
            "type": "boolean",
            "default": "False"
        }
    }
    _CONFIG_CATEGORY_NAME = 'PURGE_READ'
    _CONFIG_CATEGORY_DESCRIPTION = 'Purge the readings table'

    def __init__(self, core_mgt_address, core_mgt_port):
        self._storage = Storage(core_mgt_address, core_mgt_port)
        self._readings = Readings(core_mgt_address, core_mgt_port)
        self._logger = logger.setup("Data Purge")

    def write_statistics(self, total_purged, unsent_purged):
        loop = asyncio.get_event_loop()

        # stats = Statistics(self._storage)
        # loop.run_until_complete(stats.update('PURGED', total_purged))
        # loop.run_until_complete(stats.update('UNSNPURGED', unsent_purged))

        loop.run_until_complete(statistics.update_statistics_value('PURGED', total_purged))
        loop.run_until_complete(statistics.update_statistics_value('UNSNPURGED', unsent_purged))

    def _insert_into_log(self, level=0, log=None):
        """" INSERT into log table values """
        payload = PayloadBuilder().INSERT(code='PURGE', level=level, log=log).payload()
        self._storage.insert_into_tbl("log", payload)
        if level == 0:
            self._logger.info("PURGED SUCCESSFULLY: ", log)
        elif level == 2:
            self._logger.warning("PURGED REMOVED UNSENT ROWS: ", log)
        else:
            self._logger.error("ROWS FAILED TO REMOVE: ", log)

    def set_configuration(self):
        """" set the default configuration for purge
        :return:
            Configuration information that was set for purge process
        """
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(configuration_manager.create_category(self._CONFIG_CATEGORY_NAME,
                                                                            self._DEFAULT_PURGE_CONFIG,
                                                                            self._CONFIG_CATEGORY_DESCRIPTION))
        return event_loop.run_until_complete(configuration_manager.get_category_all_items(self._CONFIG_CATEGORY_NAME))

    def purge_data(self, config):
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
        result = self._storage.query_tbl_with_payload("readings", payload)
        total_count = result['rows'][0]['count_*']

        payload = PayloadBuilder().AGGREGATE(["min", "last_object"]).payload()
        result = self._storage.query_tbl_with_payload("streams", payload)
        last_id = result["rows"][0]["min_last_object"] if result["count"] == 1 else 0

        """ Error Levels:
            - 0: No errors
            - 1: Rows failed to remove
            - 2: Unsent rows were removed
        """
        error_level = 0

        flag = "purge" if config['retainUnsent']['value'] == "False" else "retain"
        result = self._readings.purge(age=config['age']['value'], sent_id=last_id, flag=flag)

        if "message" in result.keys() and "409 Conflict" in result["message"]:
            error_level = 1
        else:
            total_count = result['readings']
            total_rows_removed = result['removed']
            unsent_rows_removed = result['unsentPurged']
            unsent_retained = result['unsentRetained']

            if result['unsentPurged'] != 0:
                error_level = 2

        end_time = time.strftime('%Y-%m-%d %H:%M:%S.%s', time.localtime(time.time()))

        self._insert_into_log(level=error_level, log={"start_time": start_time, "end_time": end_time,
                                                      "rowsRemoved": total_rows_removed,
                                                      "unsentRowsRemoved": unsent_rows_removed,
                                                      "rowsRetained": unsent_retained, "rowsRemaining": total_count})

        return total_rows_removed, unsent_rows_removed

    def start(self):
        """" Starts the purge task

            1. Write and read Purge task configuration
            2. Purge as per the configuration
            3. Collect statistics
            4. Write statistics to statistics table
        """
        try:
            config = self.set_configuration()
            total_purged, unsent_purged = self.purge_data(config)
            self.write_statistics(total_purged, unsent_purged)
        except Exception as ex:
            self._logger.exception(str(ex))
