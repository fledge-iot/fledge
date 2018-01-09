# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web

from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.services.core import connect


__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    -------------------------------------------------------------------------------
    | GET             | /foglamp/statistics                                       |
    | GET             | /foglamp/statistics/history                               |
    -------------------------------------------------------------------------------
"""


#################################
#  Statistics
#################################


async def get_statistics(request):
    """
    Args:
        request:

    Returns:
            a general set of statistics

    :Example:
            curl -X GET http://localhost:8081/foglamp/statistics
    """
    payload = PayloadBuilder().SELECT(("key", "description", "value")).ORDER_BY(["key"]).payload()
    storage_client = connect.get_storage()
    results = storage_client.query_tbl_with_payload('statistics', payload)

    return web.json_response(results['rows'])


async def get_statistics_history(request):
    """
    Args:
        request:

    Returns:
            a list of general set of statistics

    :Example:
            curl -X GET http://localhost:8081/foglamp/statistics/history?limit=1
    """
    storage_client = connect.get_storage()
    payload = PayloadBuilder().SELECT(("history_ts", "key", "value")).payload()

    if 'limit' in request.query and request.query['limit'] != '':
        try:
            limit = int(request.query['limit'])
            if limit < 0:
                raise ValueError
            # FIXME: Hack straight away multiply the LIMIT by the group count
            # i.e. there are 8 records per distinct (stats_key), so if limit supplied is 2
            # then internally, we should calculate LIMIT *8
            # TODO: FOGL-663 Need support for "subquery" from storage service
            # Remove python side handling date_trunc and use
            # SELECT date_trunc('second', history_ts::timestamptz)::varchar as history_ts

            payload = PayloadBuilder().AGGREGATE(["count", "*"]).payload()
            result = storage_client.query_tbl_with_payload("statistics", payload)
            key_count = result['rows'][0]['count_*']

            payload = PayloadBuilder().SELECT(("history_ts", "key", "value")).LIMIT(limit * key_count).payload()

        except ValueError:
            raise web.HTTPBadRequest(reason="Limit must be a positive integer")

    result_from_storage = storage_client.query_tbl_with_payload('statistics_history', payload)

    result_without_microseconds = []
    for row in result_from_storage['rows']:
        # Remove microseconds
        new_dict = {'history_ts': row['history_ts'][:-13], row['key']: row['value']}
        result_without_microseconds.append(new_dict)

    # sorted on history_ts
    sorted_result = sorted(result_without_microseconds, key=lambda k: k['history_ts'])

    results = []
    temp_dict = {}
    previous_ts = None
    for row in sorted_result:
        # first time or when history_ts changes
        if previous_ts is None or previous_ts != row['history_ts']:
            if previous_ts is not None:
                results.append(temp_dict)
            previous_ts = row['history_ts']
            temp_dict = {'history_ts': previous_ts}

        # Append statistics key to temp dict
        for key, value in row.items():
            temp_dict.update({key: value})

    # Append the last set of records which do not get appended above
    results.append(temp_dict)

    # SELECT schedule_interval FROM schedules WHERE process_name='stats collector'
    payload = PayloadBuilder().SELECT("schedule_interval").WHERE(['process_name', '=', 'stats collector']).payload()
    result = storage_client.query_tbl_with_payload('schedules', payload)
    if len(result['rows']) > 0:
        time_str = result['rows'][0]['schedule_interval']
        ftr = [3600, 60, 1]
        interval_in_secs = sum([a * b for a, b in zip(ftr, map(int, time_str.split(':')))])
    else:
        raise web.HTTPBadRequest(reason="No stats collector schedule found")

    return web.json_response({"interval": interval_in_secs, 'statistics': results})
