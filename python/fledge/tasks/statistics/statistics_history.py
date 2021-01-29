#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Statistics history task

Fetch information from the statistics table, compute delta and
stores the delta value (statistics.value - statistics.previous_value) in the statistics_history table
"""
import json

from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common import logger
from fledge.common.process import FledgeProcess
from fledge.common import utils as common_utils

__author__ = "Ori Shadmon, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSI Soft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class StatisticsHistory(FledgeProcess):

    _logger = None

    def __init__(self):
        super().__init__()
        self._logger = logger.setup("StatisticsHistory")

    async def _bulk_update_previous_value(self, payload):
        """ UPDATE previous_value of column to have the same value as snapshot
    
        Query: 
            UPDATE statistics_history SET previous_value = value WHERE key = key
        Args:
           payload: dict containing statistics keys and previous values
        """
        await self._storage_async.update_tbl("statistics", json.dumps(payload, sort_keys=False))

    async def run(self):
        """ SELECT against the statistics table, to get a snapshot of the data at that moment.
    
        Based on the snapshot:
            1. INSERT the delta between `value` and `previous_value` into  statistics_history
            2. UPDATE the previous_value in statistics table to be equal to statistics.value at snapshot 
        """
        current_time = common_utils.local_timestamp()
        results = await self._storage_async.query_tbl("statistics")
        # Bulk updates payload
        payload = {"updates": []}
        # Bulk inserts payload
        insert_payload = {"inserts": []}
        for r in results['rows']:
            key = r['key']
            value = int(r["value"])
            previous_value = int(r["previous_value"])
            delta = value - previous_value
            payload_item = PayloadBuilder().SET(previous_value=value).WHERE(["key", "=", key]).payload()
            # Add element to bulk updates
            payload['updates'].append(json.loads(payload_item))
            # Add element to bulk inserts
            insert_payload['inserts'].append({'key': key, 'value': delta, 'history_ts': current_time})
        # Bulk inserts
        await self._storage_async.insert_into_tbl("statistics_history", json.dumps(insert_payload))
        # Bulk updates
        await self._bulk_update_previous_value(payload)
