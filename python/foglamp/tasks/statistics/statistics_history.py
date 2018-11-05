#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Statistics history task

Fetch information from the statistics table, compute delta and
stores the delta value (statistics.value - statistics.previous_value) in the statistics_history table
"""

from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common import logger
from foglamp.common.process import FoglampProcess
from foglamp.plugins.common import utils


__author__ = "Ori Shadmon, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class StatisticsHistory(FoglampProcess):

    _logger = None

    def __init__(self):
        super().__init__()
        self._logger = logger.setup("StatisticsHistory")

    async def _insert_into_stats_history(self, key='', value=0, history_ts=None):
        """ INSERT values in statistics_history
    
        Args:
            key: corresponding stats_key_value 
            value: delta between `value` and `prev_val`
            history_ts: timestamp with timezone
        Returns:
            Return the number of rows inserted. Since each process inserts only 1 row,
            the expected count should always be 1.
        """
        payload = PayloadBuilder().INSERT(key=key, value=value, history_ts=history_ts).payload()
        await self._storage_async.insert_into_tbl("statistics_history", payload)

    async def _update_previous_value(self, key='', value=0):
        """ UPDATE previous_value of column to have the same value as snapshot
    
        Query: 
            UPDATE statistics_history SET previous_value = value WHERE key = key
        Args:
            key: Key which previous_value gets update 
            value: value at snapshot
        """
        payload = PayloadBuilder().SET(previous_value=value).WHERE(["key", "=", key]).payload()
        await self._storage_async.update_tbl("statistics", payload)

    async def run(self):
        """ SELECT against the statistics table, to get a snapshot of the data at that moment.
    
        Based on the snapshot:
            1. INSERT the delta between `value` and `previous_value` into  statistics_history
            2. UPDATE the previous_value in statistics table to be equal to statistics.value at snapshot 
        """
        current_time = utils.local_timestamp()
        results = await self._storage_async.query_tbl("statistics")
        for r in results['rows']:
            key = r['key']
            value = int(r["value"])
            previous_value = int(r["previous_value"])
            delta = value - previous_value
            await self._insert_into_stats_history(key=key, value=delta, history_ts=current_time)
            await self._update_previous_value(key=key, value=value)
