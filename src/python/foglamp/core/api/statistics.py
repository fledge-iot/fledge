# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web

from foglamp.storage.payload_builder import PayloadBuilder
from foglamp.core import connect


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
    _storage = connect.get_storage()
    results = _storage.query_tbl_with_payload('statistics', payload)

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

    limit = int(request.query.get('limit')) if 'limit' in request.query else 0
    if limit == 0:
        # Return all records
        payload = PayloadBuilder().SELECT(("history_ts", "key", "value")) \
            .payload()
    else:
        # Return <limit> set of records
        # FIXME: Hack straight away multiply the LIMIT by the group count
        # i.e. there are 8 records per distinct ts, so if limit supplied is 2
        # then internally, we should calculate LIMIT 16 and so on
        # TODO: FOGL-663 Need support for "subquery" from storage service
        # Remove python side handling date_trunc and use
        # SELECT date_trunc('second', history_ts::timestamptz)::varchar as history_ts
        payload = PayloadBuilder().SELECT(("history_ts", "key", "value")) \
            .LIMIT(limit*8).payload()

    _storage = connect.get_storage()
    result_from_storage = _storage.query_tbl_with_payload('statistics_history', payload)

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

    # TODO: find out where from this "interval" will be picked and what will be its role in query?
    return web.json_response({"interval": 5, 'statistics': results})
