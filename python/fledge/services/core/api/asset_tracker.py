# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END
import json

from aiohttp import web
import urllib.parse

from fledge.common import utils as common_utils
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core import connect

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -----------------------------------------------------------------------------------------
    | GET                |    /fledge/track                                                 |
    | PUT                |    /fledge/track/service/{service}/asset/{asset}/event/{event}   |
    -----------------------------------------------------------------------------------------
"""


async def get_asset_tracker_events(request: web.Request) -> web.Response:
    """
    Args:
        request:

    Returns:
            asset track records

    :Example:
            curl -sX GET http://localhost:8081/fledge/track
            curl -sX GET http://localhost:8081/fledge/track?asset=XXX
            curl -sX GET http://localhost:8081/fledge/track?event=XXX
            curl -sX GET http://localhost:8081/fledge/track?service=XXX
            curl -sX GET http://localhost:8081/fledge/track?event=XXX&asset=XXX&service=XXX
    """
    payload = PayloadBuilder().SELECT("asset", "event", "service", "fledge", "plugin", "ts", "deprecated_ts") \
        .ALIAS("return", ("ts", 'timestamp')).FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")) \
        .ALIAS("return", ("deprecated_ts", 'deprecatedTimestamp')) \
        .WHERE(['1', '=', 1])
    if 'asset' in request.query and request.query['asset'] != '':
        asset = urllib.parse.unquote(request.query['asset'])
        payload.AND_WHERE(['asset', '=', asset])
    if 'event' in request.query and request.query['event'] != '':
        event = request.query['event']
        payload.AND_WHERE(['event', '=', event])
    if 'service' in request.query and request.query['service'] != '':
        service = urllib.parse.unquote(request.query['service'])
        payload.AND_WHERE(['service', '=', service])

    storage_client = connect.get_storage_async()
    payload = PayloadBuilder(payload.chain_payload())
    try:
        result = await storage_client.query_tbl_with_payload('asset_tracker', payload.payload())
        response = result['rows']
    except KeyError:
        msg = result['message']
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({'track': response})


async def deprecate_asset_track_entry(request: web.Request) -> web.Response:
    """
    Args:
        request:

    Returns:
            message

    :Example:
            curl -sX PUT http://localhost:8081/fledge/track/service/XXX/asset/XXX/event/XXXX
    """
    svc_name = request.match_info.get('service', None)
    asset_name = request.match_info.get('asset', None)
    event_name = request.match_info.get('event', None)
    try:
        storage_client = connect.get_storage_async()
        select_payload = PayloadBuilder().SELECT("service").WHERE(
            ['service', '=', svc_name]).AND_WHERE(['asset', '=', asset_name]).AND_WHERE(
            ['event', '=', event_name]).payload()
        get_result = await storage_client.query_tbl_with_payload('asset_tracker', select_payload)
        if 'rows' in get_result:
            response = get_result['rows']
            if response:
                # Update deprecated ts column entry
                current_time = common_utils.local_timestamp()
                update_payload = PayloadBuilder().SET(deprecated_ts=current_time).WHERE(
                    ['service', '=', svc_name]).AND_WHERE(['asset', '=', asset_name]).AND_WHERE(
                    ['event', '=', event_name]).payload()
                update_result = await storage_client.update_tbl("asset_tracker", update_payload)
                if 'response' in update_result:
                    response = update_result['response']
                    if response != 'updated':
                        raise KeyError('Update failure in asset tracker for service: {} asset: {} event: {}'.format(
                            svc_name, asset_name, event_name))
                else:
                    raise StorageServerError
            else:
                raise ValueError('No record found in asset tracker for given service: {} asset: {} event: {}'.format(
                    svc_name, asset_name, event_name))
        else:
            raise StorageServerError
    except StorageServerError as err:
        msg = str(err)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": "Storage error: {}".format(msg)}))
    except KeyError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response({'success': "Asset record entry has been deprecated."})
