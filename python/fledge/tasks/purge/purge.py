# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END
"""
Purge readings based on the age of the readings.

Readings data that is older than the specified age will be removed from the readings store.

Conditions:
    1. purge unsent - all readings older than the configured age | size, regardless of the minimum(last_object) of streams table will be removed.

    2. retain unsent to any destination / retain unsent to all destinations
        Allow the user the option to retain readings if they have not been sent to at least one destination or
        retain readings if they have not been sent to all destinations.

        retain unsent to any destination
            Readings with an id value that is greater than the maximum(last_object) of streams table will not be removed.

        retain unsent to all destinations
            Readings with an id value that is greater than the minimum(last_object) of streams table will not be removed.

Statistics reported by Purge process are:
    -> Readings removed
    -> Unsent readings removed
    -> Readings retained (based on retainUnsent configuration)
    -> Remaining readings
    All these statistics are inserted into the log table
"""
import time

from datetime import datetime, timedelta, timezone

from fledge.common import statistics
from fledge.common.audit_logger import AuditLogger
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.logger import FLCoreLogger
from fledge.common.process import FledgeProcess
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.exceptions import *


__author__ = "Ori Shadmon, Vaibhav Singhal, Mark Riddoch, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class Purge(FledgeProcess):

    _DEFAULT_PURGE_CONFIG = {
        "age": {
            "description": "Age of data to be retained (in hours). All data older than this value will be removed," +
                           "unless retained.",
            "type": "integer",
            "default": "72",
            "displayName": "Age Of Data To Be Retained (In Hours)",
            "order": "1"
        },
        "size": {
            "description": "Maximum number of rows of data to be retained. Oldest data will be removed to keep "
                           "below this row count, unless retained.",
            "type": "integer",
            "default": "1000000",
            "displayName": "Max rows of data to retain",
            "order": "2"
        },
        "retainUnsent": {
            "description": "Retain data that has not been sent yet.",
            "type": "enumeration",
            "options": ["purge unsent", "retain unsent to any destination", "retain unsent to all destinations"],
            "default": "purge unsent",
            "displayName": "Retain Unsent Data",
            "order": "3"
        },
        "retainStatsHistory": {
            "description": "This is the measure of how long to retain statistics history data for and should be measured in days.",
            "type": "integer",
            "default": "30",
            "displayName": "Retain Stats History Data (In Days)",
            "order": "4",
            "minimum": "1"
        },
        "retainAuditLog": {
            "description": "This is the measure of how long to retain audit trail information for and should be measured in days.",
            "type": "integer",
            "default": "60",
            "displayName": "Retain Audit Trail Data (In Days)",
            "order": "5",
            "minimum": "1"
        }
    }
    _CONFIG_CATEGORY_NAME = 'PURGE_READ'
    _CONFIG_CATEGORY_DESCRIPTION = 'Purge the readings, log, statistics history table'

    def __init__(self):
        super().__init__()
        self._logger = FLCoreLogger().get_logger("Data Purge")
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
                                          self._CONFIG_CATEGORY_DESCRIPTION, True, display_name="Purge")

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
        duration = 0
        method = None

        start_time = datetime.now(timezone.utc).isoformat(' ')

        if config['retainUnsent']['value'].lower() == "purge unsent":
            flag = "purge"
            operation_type = "min"

        elif config['retainUnsent']['value'].lower() == "retain unsent to any destination":
            flag = "retainany"
            operation_type = "max"

        else:
            flag = "retainall"
            operation_type = "min"

        # Identifies the row id to use
        north_instance = []
        north_list = []
        payload_north_streams = PayloadBuilder().SELECT("description").WHERE(['active', '=', 't']).payload()
        north_streams = await self._storage_async.query_tbl_with_payload("streams", payload_north_streams)
        for item in north_streams["rows"]:
            if "description" in north_list:
                north_list.append(item["description"])

        self._logger.debug("purge_data - north configured :{}: north active :{}: ".format(north_streams, north_list))

        if north_list:
            payload_sched = PayloadBuilder().SELECT("schedule_name").WHERE(
                ['schedule_name', 'in', north_list]).AND_WHERE(['enabled', '=', 't']).payload()
            north_instance = await self._storage_async.query_tbl_with_payload("schedules", payload_sched)

            north_list = []
            for item in north_instance["rows"]:
                if "schedule_name" in north_list:
                    north_list.append(item["schedule_name"])

        self._logger.debug("purge_data - north schedules - schedules - :{}: north enabled :{}: ".format(north_instance,
                                                                                                        north_list))

        if north_list:
            payload = PayloadBuilder().AGGREGATE([operation_type, "last_object"]).\
                        WHERE(['description', 'in', north_list])\
                        .payload()
        else:
            payload = PayloadBuilder().AGGREGATE([operation_type, "last_object"]).payload()

        result = await self._storage_async.query_tbl_with_payload("streams", payload)

        if operation_type == "min":
            last_object = result["rows"][0]["min_last_object"]
        else:
            last_object = result["rows"][0]["max_last_object"]

        self._logger.debug("purge_data - last_object :{}: ".format(last_object))

        if result["count"] == 1:
            # FIXME: Remove below check when fix from storage layer
            # Below check is required as If no streams entry exists in DB storage layer returns response as below:
            # {'rows': [{'min_last_object': ''}], 'count': 1}
            # BTW it should return integer i.e 0 not in string
            last_id = 0 if last_object == '' else last_object
        else:
            last_id = 0

        self._logger.debug("purge_data - flag :{}: last_id :{}: count :{}: operation_type :{}:".format(
            flag, last_id, result["count"], operation_type))

        # Do the purge by rows first as it is cheaper than doing the purge by age and
        # may result in less rows for purge by age to operate on.
        try:
            if int(config['size']['value']) != 0:
                result = await self._readings_storage_async.purge(size=config['size']['value'], sent_id=last_id,
                                                                  flag=flag)
                if result is not None:
                    total_rows_removed = result['removed']
                    unsent_rows_removed = result['unsentPurged']
                    unsent_retained = result['unsentRetained']
                    duration = result['duration']
                    if method is None:
                        method = result['method']
                    else:
                        method += " and "
                        method += result['method']
        except ValueError:
            self._logger.error("purge_data - Configuration item size {} should be integer!".format(
                config['size']['value']))
        except StorageServerError:
            # skip logging as its already done in details for this operation in case of error
            # FIXME: check if ex.error jdoc has retryable True then retry the operation else move on
            pass
        try:
            if int(config['age']['value']) != 0:
                result = await self._readings_storage_async.purge(age=config['age']['value'], sent_id=last_id,
                                                                  flag=flag)
                if result is not None:
                    total_rows_removed += result['removed']
                    unsent_rows_removed += result['unsentPurged']
                    unsent_retained = result['unsentRetained']
                    duration += result['duration']
                    method = result['method']
        except ValueError:
            self._logger.error("purge_data - Configuration item age {} should be integer!".format(
                config['age']['value']))
        except StorageServerError:
            # skip logging as its already done in details for this operation in case of error
            # FIXME: check if ex.error jdoc has retryable True then retry the operation else move on
            pass
        end_time = datetime.now(timezone.utc).isoformat(' ')

        if total_rows_removed > 0:
            """ Only write an audit log entry when rows are removed """
            await self._audit.information('PURGE', {"start_time": start_time,
                                                    "end_time": end_time,
                                                    "rowsRemoved": total_rows_removed,
                                                    "unsentRowsRemoved": unsent_rows_removed,
                                                    "rowsRetained": unsent_retained,
                                                    "duration": duration,
                                                    "method": method
                                                    })
        else:
            self._logger.info("No rows purged")

        return total_rows_removed, unsent_rows_removed

    async def purge_stats_history(self, config):
        """" Purge statistics history table based on the Age which is defined in retainStatsHistory config item
        """
        ts = datetime.now() - timedelta(days=int(config['retainStatsHistory']['value']))
        payload = PayloadBuilder().WHERE(['history_ts', '<=', str(ts)]).payload()
        await self._storage_async.delete_from_tbl("statistics_history", payload)

    async def purge_audit_trail_log(self, config):
        """" Purge log table based on the Age which is defined under in config item
        """
        ts = datetime.now() - timedelta(days=int(config['retainAuditLog']['value']))
        payload = PayloadBuilder().WHERE(['ts', '<=', str(ts)]).payload()
        await self._storage_async.delete_from_tbl("log", payload)

    async def run(self):
        """" Starts the purge task

            1. Write and read Purge task configuration
            2. Purge as per the configuration
            3. Collect statistics
            4. Write statistics to statistics table
        """
        try:
            config = await self.set_configuration()
            if self.is_dry_run():
                return
            total_purged, unsent_purged = await self.purge_data(config)
            await self.write_statistics(total_purged, unsent_purged)
            await self.purge_stats_history(config)
            await self.purge_audit_trail_log(config)
        except Exception as ex:
            self._logger.exception(ex)
