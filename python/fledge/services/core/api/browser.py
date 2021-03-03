# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""
Experimental browser for extracting reading data from the Fledge data buffer

Supports a number of REST API:

  http://<address>/fledge/asset
     - Return a summary count of all asset readings
  http://<address>/fledge/asset/{asset_code}
    - Return a set of asset readings for the given asset
  http://<address>/fledge/asset/{asset_code}/summary
    - Return a set of the summary of all sensors values for the given asset
  http://<address>/fledge/asset/{asset_code}/{reading}
    - Return a set of sensor readings for the specified asset and sensor
  http://<address>/fledge/asset/{asset_code}/{reading}/summary
    - Return a summary (min, max and average) for the specified asset and sensor
  http://<address>/fledge/asset/{asset_code}/{reading}/series
    - Return a time series (min, max and average) for the specified asset and
      sensor averages over seconds, minutes or hours. The selection of seconds, minutes
      or hours is done via the group query parameter

  All but the /fledge/asset API call take a set of optional query parameters
    limit=x     Return the first x rows only
    skip=x      skip first n entries and used with limit to implemented paged interfaces
    seconds=x   Limit the data return to be less than x seconds old
    minutes=x   Limit the data returned to be less than x minutes old
    hours=x     Limit the data returned to be less than x hours old

  Note: seconds, minutes and hours can not be combined in a URL. If they are then only seconds
  will have an effect.
  Note: if datetime units are supplied then limit will not respect i.e mutually exclusive
"""
import time
import datetime
import json

from aiohttp import web

from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core import connect
from fledge.common import logger

_logger = logger.setup(__name__)

__author__ = "Mark Riddoch, Ashish Jabble, Massimiliano Pinto"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


__DEFAULT_LIMIT = 20
__DEFAULT_OFFSET = 0


def setup(app):
    """ Add the routes for the API endpoints supported by the data browser """
    app.router.add_route('GET', '/fledge/asset', asset_counts)
    app.router.add_route('GET', '/fledge/asset/{asset_code}', asset)
    app.router.add_route('GET', '/fledge/asset/{asset_code}/summary', asset_all_readings_summary)
    app.router.add_route('GET', '/fledge/asset/{asset_code}/{reading}', asset_reading)
    app.router.add_route('GET', '/fledge/asset/{asset_code}/{reading}/summary', asset_summary)
    app.router.add_route('GET', '/fledge/asset/{asset_code}/{reading}/series', asset_averages)
    app.router.add_route('GET', '/fledge/asset/{asset_code}/bucket/{bucket_size}', asset_datapoints_with_bucket_size)
    app.router.add_route('GET', '/fledge/asset/{asset_code}/{reading}/bucket/{bucket_size}', asset_readings_with_bucket_size)
    app.router.add_route('GET', '/fledge/structure/asset', asset_structure)


def prepare_limit_skip_payload(request, _dict):
    """ limit skip clause validation

    Args:
        request: request query params
        _dict: main payload dict
    Returns:
        chain payload dict
    """
    limit = __DEFAULT_LIMIT
    if 'limit' in request.query and request.query['limit'] != '':
        try:
            limit = int(request.query['limit'])
            if limit < 0:
                raise ValueError
        except ValueError:
            raise web.HTTPBadRequest(reason="Limit must be a positive integer")

    offset = __DEFAULT_OFFSET
    if 'skip' in request.query and request.query['skip'] != '':
        try:
            offset = int(request.query['skip'])
            if offset < 0:
                raise ValueError
        except ValueError:
            raise web.HTTPBadRequest(reason="Skip/Offset must be a positive integer")

    payload = PayloadBuilder(_dict).LIMIT(limit)
    if offset:
        payload = PayloadBuilder(_dict).SKIP(offset)

    return payload.chain_payload()


async def asset_counts(request):
    """ Browse all the assets for which we have recorded readings and
    return a readings count.

    Returns:
           json result on basis of SELECT asset_code, count(*) FROM readings GROUP BY asset_code;

    :Example:
            curl -sX GET http://localhost:8081/fledge/asset
    """
    payload = PayloadBuilder().AGGREGATE(["count", "*"]).ALIAS("aggregate", ("*", "count", "count")) \
        .GROUP_BY("asset_code").payload()

    results = {}
    try:
        _readings = connect.get_readings_async()
        results = await _readings.query(payload)
        response = results['rows']
        asset_json = [{"count": r['count'], "assetCode": r['asset_code']} for r in response]
    except KeyError:
        raise web.HTTPBadRequest(reason=results['message'])
    else:
        return web.json_response(asset_json)


async def asset(request):
    """ Browse a particular asset for which we have recorded readings and
    return a readings with timestamps for the asset. The number of readings
    return is defaulted to a small number (20), this may be changed by supplying
    the query parameter ?limit=xx&skip=xx and it will not respect when datetime units is supplied
    Can also output the readings in ascending or descending order. For that give query parameter
    ?order=asc or ?order=desc . If nothing given in order then default is descending.
    Returns:
          json result on basis of SELECT user_ts as "timestamp", (reading)::jsonFROM readings WHERE asset_code = 'asset_code' ORDER BY user_ts DESC LIMIT 20 OFFSET 0;

    :Example:
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity?limit=1
            curl -sX GET "http://localhost:8081/fledge/asset/fogbench_humidity?limit=1&skip=1
            curl -sX GET "http://localhost:8081/fledge/asset/fogbench_humidity?limit=1&skip=1&order=asc
            curl -sX GET "http://localhost:8081/fledge/asset/fogbench_humidity?limit=1&skip=1&order=desc
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity?seconds=60
    """
    asset_code = request.match_info.get('asset_code', '')
    _select = PayloadBuilder().SELECT(("reading", "user_ts")).ALIAS("return", ("user_ts", "timestamp")).chain_payload()

    _where = PayloadBuilder(_select).WHERE(["asset_code", "=", asset_code]).chain_payload()
    if 'seconds' in request.query or 'minutes' in request.query or 'hours' in request.query:
        _and_where = where_clause(request, _where)
    else:
        # Add the order by and limit, offset clause
        _and_where = prepare_limit_skip_payload(request, _where)

    # check the order. keep the default order desc
    _order = 'desc'
    if 'order' in request.query:
        _order = request.query['order']
        if _order not in ('asc', 'desc'):
            msg = "order must be asc or desc"
            raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))

    payload = PayloadBuilder(_and_where).ORDER_BY(["user_ts", _order]).payload()
    results = {}
    try:
        _readings = connect.get_readings_async()
        results = await _readings.query(payload)
        response = results['rows']
    except KeyError:
        msg = results['message']
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response(response)


async def asset_reading(request):
    """ Browse a particular sensor value of a particular asset for which we have recorded readings and
    return the timestamp and reading value for that sensor. The number of rows returned
    is limited to a small number, this number may be altered by use of
    the query parameter limit=xxx&skip=xxx and it will not respect when datetime units is supplied

    The readings returned can also be time limited by use of the query
    parameter seconds=sss. This defines a number of seconds that the reading
    must have been processed in. Older readings than this will not be returned.

    The readings returned can also be time limited by use of the query
    parameter minutes=mmm. This defines a number of minutes that the reading
    must have been processed in. Older readings than this will not be returned.

    The readings returned can also be time limited by use of the query
    parameter hours=hh. This defines a number of hours that the reading
    must have been processed in. Older readings than this will not be returned.

    Only one of hour, minutes or seconds should be supplied

    Returns:
           json result on basis of SELECT user_ts as "timestamp", reading->>'reading' FROM readings WHERE asset_code = 'asset_code' ORDER BY user_ts DESC LIMIT 20 OFFSET 0;

    :Example:
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/temperature
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/temperature?limit=1
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/temperature?skip=10
            curl -sX GET "http://localhost:8081/fledge/asset/fogbench_humidity/temperature?limit=1&skip=10"
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/temperature?minutes=60
    """
    asset_code = request.match_info.get('asset_code', '')
    reading = request.match_info.get('reading', '')

    _select = PayloadBuilder().SELECT(("user_ts", ["reading", reading])) \
        .ALIAS("return", ("user_ts", "timestamp"), ("reading", reading)).chain_payload()
    _where = PayloadBuilder(_select).WHERE(["asset_code", "=", asset_code]).chain_payload()
    if 'seconds' in request.query or 'minutes' in request.query or 'hours' in request.query:
        _and_where = where_clause(request, _where)
    else:
        # Add the order by and limit, offset clause
        _and_where = prepare_limit_skip_payload(request, _where)

    payload = PayloadBuilder(_and_where).ORDER_BY(["user_ts", "desc"]).payload()

    results = {}
    try:
        _readings = connect.get_readings_async()
        results = await _readings.query(payload)
        response = results['rows']
    except KeyError:
        raise web.HTTPBadRequest(reason=results['message'])
    else:
        return web.json_response(response)


async def asset_all_readings_summary(request):
    """ Browse all the assets for which we have recorded readings and
    return a summary for all sensors values for an asset code. The values that are
    returned are the min, max and average values of the sensor.

    Only one of hour, minutes or seconds should be supplied, if more than one time unit
    then the smallest unit will be picked

    The number of records return is default to a small number (20), this may be changed by supplying
    the query parameter ?limit=xx&skip=xx and it will not respect when datetime units is supplied

    :Example:
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/summary
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/summary?seconds=60
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/summary?limit=10
    """
    try:
        # Get readings from asset_code
        asset_code = request.match_info.get('asset_code', '')
        # TODO: Use only the latest asset read to determine the data points to use. This
        # avoids reading every single reading into memory and creating a very big result set See FOGL-2635
        payload = PayloadBuilder().SELECT("reading").WHERE(["asset_code", "=", asset_code]).LIMIT(1).ORDER_BY(["user_ts", "desc"]).payload()
        _readings = connect.get_readings_async()
        results = await _readings.query(payload)
        if not results['rows']:
            raise web.HTTPNotFound(reason="{} asset_code not found".format(asset_code))

        # TODO: FOGL-1768 when support available from storage layer then avoid multiple calls
        # Find keys in readings
        reading_keys = list(results['rows'][-1]['reading'].keys())
        response = []
        _where = PayloadBuilder().WHERE(["asset_code", "=", asset_code]).chain_payload()
        if 'seconds' in request.query or 'minutes' in request.query or 'hours' in request.query:
            _and_where = where_clause(request, _where)
        else:
            # Add limit, offset clause
            _and_where = prepare_limit_skip_payload(request, _where)

        for reading in reading_keys:
            _aggregate = PayloadBuilder(_and_where).AGGREGATE(["min", ["reading", reading]],
                                                              ["max", ["reading", reading]],
                                                              ["avg", ["reading", reading]]) \
                .ALIAS('aggregate', ('reading', 'min', 'min'),
                       ('reading', 'max', 'max'),
                       ('reading', 'avg', 'average')).chain_payload()
            payload = PayloadBuilder(_aggregate).payload()
            results = await _readings.query(payload)
            response.append({reading: results['rows'][0]})
    except (KeyError, IndexError) as ex:
        raise web.HTTPNotFound(reason=ex)
    except (TypeError, ValueError) as ex:
        raise web.HTTPBadRequest(reason=ex)
    else:
        return web.json_response(response)


async def asset_summary(request):
    """ Browse all the assets for which we have recorded readings and
    return a summary for a particular sensor. The values that are
    returned are the min, max and average values of the sensor.

    The readings summarised can also be time limited by use of the query
    parameter seconds=sss. This defines a number of seconds that the reading
    must have been processed in. Older readings than this will not be summarised.

    The readings summarised can also be time limited by use of the query
    parameter minutes=mmm. This defines a number of minutes that the reading
    must have been processed in. Older readings than this will not be summarised.

    The readings summarised can also be time limited by use of the query
    parameter hours=hh. This defines a number of hours that the reading
    must have been processed in. Older readings than this will not be summarised.

    Only one of hour, minutes or seconds should be supplied

    Returns:
           json result on basis of SELECT MIN(reading->>'reading'), MAX(reading->>'reading'), AVG((reading->>'reading')::float) FROM readings WHERE asset_code = 'asset_code';

    :Example:
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/temperature/summary
    """
    asset_code = request.match_info.get('asset_code', '')
    reading = request.match_info.get('reading', '')
    try:
        payload = PayloadBuilder().SELECT("reading").WHERE(["asset_code", "=", asset_code]).LIMIT(1).ORDER_BY(
            ["user_ts", "desc"]).payload()
        _readings = connect.get_readings_async()
        results = await _readings.query(payload)
        if not results['rows']:
            raise web.HTTPNotFound(reason="{} asset_code not found".format(asset_code))

        # TODO: FOGL-1768 when support available from storage layer then avoid multiple calls
        reading_keys = list(results['rows'][-1]['reading'].keys())
        if reading not in reading_keys:
            raise web.HTTPNotFound(reason="{} reading key is not found".format(reading))

        _aggregate = PayloadBuilder().AGGREGATE(["min", ["reading", reading]], ["max", ["reading", reading]],
                                                ["avg", ["reading", reading]]) \
            .ALIAS('aggregate', ('reading', 'min', 'min'), ('reading', 'max', 'max'),
                   ('reading', 'avg', 'average')).chain_payload()
        _where = PayloadBuilder(_aggregate).WHERE(["asset_code", "=", asset_code]).chain_payload()
        _and_where = where_clause(request, _where)
        payload = PayloadBuilder(_and_where).payload()
        results = await _readings.query(payload)
        # for aggregates, so there can only ever be one row
        response = results['rows'][0]
    except KeyError:
        raise web.HTTPBadRequest(reason=results['message'])
    else:
        return web.json_response({reading: response})


async def asset_averages(request):
    """ Browse all the assets for which we have recorded readings and
    return a series of averages per second, minute or hour.

    The readings averaged can also be time limited by use of the query
    parameter seconds=sss. This defines a number of seconds that the reading
    must have been processed in. Older readings than this will not be summarised.

    The readings averaged can also be time limited by use of the query
    parameter minutes=mmm. This defines a number of minutes that the reading
    must have been processed in. Older readings than this will not be summarised.

    The readings averaged can also be time limited by use of the query
    parameter hours=hh. This defines a number of hours that the reading
    must have been processed in. Older readings than this will not be summarised.

    Only one of hour, minutes or seconds should be supplied

    The amount of time covered by each returned value is set using the
    query parameter group. This may be set to seconds, minutes or hours

    Returns:
            on the basis of
            SELECT min((reading->>'reading')::float) AS "min",
                   max((reading->>'reading')::float) AS "max",
                   avg((reading->>'reading')::float) AS "average",
                   to_char(user_ts, 'YYYY-MM-DD HH24:MI:SS') AS "timestamp"
            FROM fledge.readings
                   WHERE asset_code = 'asset_code' AND
                     reading ? 'reading'
            GROUP BY to_char(user_ts, 'YYYY-MM-DD HH24:MI:SS')
            ORDER BY timestamp DESC;

    :Example:
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/temperature/series
            curl -sX GET "http://localhost:8081/fledge/asset/fogbench_humidity/temperature/series?limit=1&skip=1"
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/temperature/series?hours=1
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/temperature/series?minutes=60
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/temperature/series?seconds=3600
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/temperature/series?group=seconds
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/temperature/series?group=minutes
            curl -sX GET http://localhost:8081/fledge/asset/fogbench_humidity/temperature/series?group=hours
    """
    asset_code = request.match_info.get('asset_code', '')
    reading = request.match_info.get('reading', '')

    ts_restraint = 'YYYY-MM-DD HH24:MI:SS'
    if 'group' in request.query and request.query['group'] != '':
        _group = request.query['group']
        if _group in ('seconds', 'minutes', 'hours'):
            if _group == 'seconds':
                ts_restraint = 'YYYY-MM-DD HH24:MI:SS'
            elif _group == 'minutes':
                ts_restraint = 'YYYY-MM-DD HH24:MI'
            elif _group == 'hours':
                ts_restraint = 'YYYY-MM-DD HH24'
        else:
            raise web.HTTPBadRequest(reason="{} is not a valid group".format(_group))

    _aggregate = PayloadBuilder().AGGREGATE(["min", ["reading", reading]], ["max", ["reading", reading]],
                                            ["avg", ["reading", reading]]) \
        .ALIAS('aggregate', ('reading', 'min', 'min'), ('reading', 'max', 'max'),
               ('reading', 'avg', 'average')).chain_payload()
    _where = PayloadBuilder(_aggregate).WHERE(["asset_code", "=", asset_code]).chain_payload()

    if 'seconds' in request.query or 'minutes' in request.query or 'hours' in request.query:
        _and_where = where_clause(request, _where)
    else:
        # Add LIMIT, OFFSET
        _and_where = prepare_limit_skip_payload(request, _where)

    # Add the GROUP BY and ORDER BY timestamp DESC
    _group = PayloadBuilder(_and_where).GROUP_BY("user_ts").ALIAS("group", ("user_ts", "timestamp")) \
        .FORMAT("group", ("user_ts", ts_restraint)).chain_payload()
    payload = PayloadBuilder(_group).ORDER_BY(["user_ts", "desc"]).payload()
    results = {}
    try:
        _readings = connect.get_readings_async()
        results = await _readings.query(payload)
        response = results['rows']
    except KeyError:
        raise web.HTTPBadRequest(reason=results['message'])
    else:
        return web.json_response(response)


def where_clause(request, where):
    val = 0
    try:
        if 'seconds' in request.query and request.query['seconds'] != '':
            val = int(request.query['seconds'])
        elif 'minutes' in request.query and request.query['minutes'] != '':
            val = int(request.query['minutes']) * 60
        elif 'hours' in request.query and request.query['hours'] != '':
            val = int(request.query['hours']) * 60 * 60

        if val < 0:
            raise ValueError
    except ValueError:
        raise web.HTTPBadRequest(reason="Time must be a positive integer")

    # if no time units then NO AND_WHERE condition applied
    if val == 0:
        return where

    payload = PayloadBuilder(where).AND_WHERE(['user_ts', 'newer', val]).chain_payload()
    return payload


async def asset_datapoints_with_bucket_size(request: web.Request) -> web.Response:
    """ Retrieve datapoints for an asset.

        If bucket_size is not given then the bucket size is 1
        If start is not given then the start point is now - 60 seconds.
        If length is not given then length is 60 seconds. And length is calculated with length / bucket_size
        For multiple assets use comma separated values in request and this will allow data from one or more asset to be returned.

       :Example:
               curl -sX GET http://localhost:8081/fledge/asset/{asset_code}/bucket/{bucket_size}
               curl -sX GET http://localhost:8081/fledge/asset/{asset_code_1},{asset_code_2}/bucket/{bucket_size}
       """
    try:
        start_found = False
        length_found = False
        asset_code = request.match_info.get('asset_code', '')
        bucket_size = request.match_info.get('bucket_size', 1)
        length = 60

        ts = datetime.datetime.timestamp(datetime.datetime.now())
        start = ts - length
        asset_code_list = asset_code.split(',')
        _readings = connect.get_readings_async()

        if 'start' in request.query and request.query['start'] != '':
            try:
                start = float(request.query['start'])
                start_found = True
            except Exception as e:
                raise ValueError('Invalid value for start. Error: {}'.format(str(e)))

        if 'length' in request.query and request.query['length'] != '':
            length = float(request.query['length'])
            if length < 0:
                raise ValueError('length must be a positive integer')
            length_found = True
            # No user start parameter: decrease default start by the user provided length
            if start_found == False:
                start = ts - length

        use_microseconds = False
        # Check subsecond request in start
        start_micros = "{:.6f}".format(start).split('.')[1]
        if start_found == True and start_micros != '000000':
            use_microseconds = True
        else:
            # No decimal part, check subsecond request in length
            start_micros = "{:.6f}".format(length).split('.')[1]
            if length_found == True and start_micros != '000000':
                use_microseconds = True

        # Build UTC datetime start/stop from start timestamp with/without microseconds
        if use_microseconds == False:
            start_date = datetime.datetime.fromtimestamp(start, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            stop_date = datetime.datetime.fromtimestamp(start + length, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        else:
            start_date = datetime.datetime.fromtimestamp(start, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
            stop_date = datetime.datetime.fromtimestamp(start + length, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

        # Prepare payload
        _aggregate = PayloadBuilder().AGGREGATE(["all"]).chain_payload()
        _and_where = PayloadBuilder(_aggregate).WHERE(["asset_code", "in", asset_code_list]).AND_WHERE([
            "user_ts", ">=", str(start_date)], ["user_ts", "<=", str(stop_date)]).chain_payload()

        _bucket = PayloadBuilder(_and_where).TIMEBUCKET('user_ts', bucket_size,
                                                        'YYYY-MM-DD HH24:MI:SS', 'timestamp').chain_payload()

        payload = PayloadBuilder(_bucket).LIMIT(int(float(length / float(bucket_size)))).payload()

        # Sort & timebucket modifiers can not be used in same payload
        # payload = PayloadBuilder(limit).ORDER_BY(["user_ts", "desc"]).payload()
        results = await _readings.query(payload)
        response = results['rows']
    except (KeyError, IndexError) as e:
        raise web.HTTPNotFound(reason=e)
    except (TypeError, ValueError) as e:
        raise web.HTTPBadRequest(reason=e)
    except Exception as e:
        raise web.HTTPInternalServerError(reason=str(e))
    else:
        return web.json_response(response)


async def asset_readings_with_bucket_size(request: web.Request) -> web.Response:
    """ Retrieve readings for a single asset between two points in time.
        These points are defined as a relative value in seconds back in time from the current time and a number of seconds worth of data.
        For example: For asset XYZ from (now - 60) for 60 seconds to get a minutes worth of data from a minute in the passed.
        The samples returned are averages grouped over a period of time, know as a bucket size.
        If 60 seconds worth of data is requested and a bucket size of 10 seconds is given then 6 values will be returned.
        Each of those 6 readings is an average over a 10 seconds period.

        If bucket_size is not given then the bucket size is 1
        If start is not given then the start point is now - 60 seconds.
        If length is not given then length is 60 seconds. And length is calculated with length / bucket_size

       :Example:
               curl -sX GET http://localhost:8081/fledge/asset/{asset_code}/{reading}/bucket/{bucket_size}
               curl -sX GET http://localhost:8081/fledge/asset/{asset_code}/{reading}/bucket/{bucket_size}?start=<start point>
               curl -sX GET http://localhost:8081/fledge/asset/{asset_code}/{reading}/bucket/{bucket_size}?length=<length>
               curl -sX GET "http://localhost:8081/fledge/asset/{asset_code}/{reading}/bucket/{bucket_size}?start=<start point>&length=<length>"
       """
    try:
        start_found = False
        asset_code = request.match_info.get('asset_code', '')
        reading = request.match_info.get('reading', '')
        bucket_size = request.match_info.get('bucket_size', 1)
        length = 60
        ts = datetime.datetime.now().timestamp()
        start = ts - 60
        _aggregate = PayloadBuilder().AGGREGATE(["min", ["reading", reading]], ["max", ["reading", reading]],
                                                ["avg", ["reading", reading]]) \
            .ALIAS('aggregate', ('reading', 'min', 'min'), ('reading', 'max', 'max'),
                   ('reading', 'avg', 'average')).chain_payload()
        _readings = connect.get_readings_async()

        if 'start' in request.query and request.query['start'] != '':
            try:
                start = float(request.query['start'])
                datetime.datetime.fromtimestamp(start)
                start_found = True
            except Exception as e:
                raise ValueError('Invalid value for start. Error: {}'.format(str(e)))

        if 'length' in request.query and request.query['length'] != '':
            length = int(request.query['length'])
            if length < 0:
                raise ValueError('length must be a positive integer')
            # No user start parameter: decrease default start by the user provided length
            if start_found == False:
                start = ts - length

        # Build datetime from timestamp
        start_time = time.gmtime(start)
        start_date = time.strftime("%Y-%m-%d %H:%M:%S", start_time)
        stop_time = time.gmtime(start + length)
        stop_date = time.strftime("%Y-%m-%d %H:%M:%S", stop_time)

        # Prepare payload
        _where = PayloadBuilder(_aggregate).WHERE(["asset_code", "=", asset_code]).AND_WHERE([
            "user_ts", ">=", str(start_date)], ["user_ts", "<=", str(stop_date)], [
            "user_ts", "<=", str(stop_date)]).chain_payload()
        _bucket = PayloadBuilder(_where).TIMEBUCKET('user_ts', bucket_size, 'YYYY-MM-DD HH24:MI:SS',
                                                    'timestamp').chain_payload()

        payload = PayloadBuilder(_bucket).LIMIT(int(length / int(bucket_size))).payload()

        # Sort & timebucket modifiers can not be used in same payload
        # payload = PayloadBuilder(limit).ORDER_BY(["user_ts", "desc"]).payload()
        results = await _readings.query(payload)
        response = results['rows']
    except (KeyError, IndexError) as e:
        raise web.HTTPNotFound(reason=e)
    except (TypeError, ValueError) as e:
        raise web.HTTPBadRequest(reason=e)
    except Exception as e:
        raise web.HTTPInternalServerError(reason=str(e))
    else:
        return web.json_response(response)


async def asset_structure(request):
    """ Browse all the assets for which we have recorded readings and
    return the asset structure

    Returns:
           json result showing the asset structure

    :Example:
            curl -sX GET http://localhost:8081/fledge/structure/asset
            {
              "AX8": {
                "datapoint": {
                  "internal": "float",
                  "spot1": "float",
                  "minRPi": "float",
                  "maxRPi": "float",
                  "averageRPi": "float",
                  "minBackupdisk": "float",
                  "maxBackupdisk": "float",
                  "averageBackupdisk": "float",
                  "minCoral": "float",
                  "maxCoral": "float",
                  "averageCoral": "float"
                },
                "metadata": {
                  "factory": "London",
                  "line": "Line 4",
                  "units": "Kelvin"
                }
              }
            }
    """
    payload = PayloadBuilder().GROUP_BY("asset_code").payload()

    results = {}
    try:
        _readings = connect.get_readings_async()
        results = await _readings.query(payload)
        rows = results['rows']
        asset_json = {}
        for row in rows:
            code = row['asset_code']
            datapoint = {}
            metadata = {}
            for name, value in row['reading'].items():
                if type(value) == str:
                    if value == "True" or value == "False":
                        datapoint[name] = "boolean"
                    else:
                        metadata[name] = value
                elif type(value) == int:
                    datapoint[name] = "integer"
                elif type(value) == float:
                    datapoint[name] = "float"
            if len(metadata) > 0:
                asset_json[code] = {'datapoint':datapoint,'metadata':metadata}
            else:
                asset_json[code] = {'datapoint':datapoint}
    except KeyError:
        msg = results['message']
        raise web.HTTPBadRequest(reason=results['message'], body=json.dumps({"message": msg}))
    except Exception as e:
        raise web.HTTPInternalServerError(reason=str(e), body=json.dumps({"message":str(e)}))
    else:
        return web.json_response(asset_json)


