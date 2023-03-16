# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END
import json

from aiohttp import web
import urllib.parse

from fledge.common import utils as common_utils
from fledge.common.audit_logger import AuditLogger
from fledge.common.logger import FLCoreLogger
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

_logger = FLCoreLogger().get_logger(__name__)


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
    payload = PayloadBuilder().SELECT("asset", "event", "service", "fledge", "plugin", "ts", "deprecated_ts", "data") \
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
        _logger.error("Failed to get asset tracker events. {}".format(msg))
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
        # TODO: FOGL-6749 Once rows affected with 0 case handled at Storage side then we can remove SELECT call
        select_payload = PayloadBuilder().SELECT("deprecated_ts").WHERE(
            ['service', '=', svc_name]).AND_WHERE(['asset', '=', asset_name]).AND_WHERE(
            ['event', '=', event_name]).payload()
        get_result = await storage_client.query_tbl_with_payload('asset_tracker', select_payload)
        if 'rows' in get_result:
            response = get_result['rows']
            if response:
                if response[0]['deprecated_ts'] == "":
                    # Update deprecated_ts column entry
                    current_time = common_utils.local_timestamp()
                    if event_name in ('Ingest', 'store'):
                        audit_event_name = "Ingest & store"
                        and_where_val = ['event', 'in', ["Ingest", "store"]]
                    else:
                        audit_event_name = event_name
                        and_where_val = ['event', '=', event_name]
                    update_payload = PayloadBuilder().SET(deprecated_ts=current_time).WHERE(
                        ['service', '=', svc_name]).AND_WHERE(['asset', '=', asset_name]).AND_WHERE(
                        and_where_val).AND_WHERE(['deprecated_ts', 'isnull']).payload()
                    update_result = await storage_client.update_tbl("asset_tracker", update_payload)
                    if 'response' in update_result:
                        response = update_result['response']
                        if response != 'updated':
                            raise KeyError('Update failure in asset tracker for service: {} asset: {} event: {}'.format(
                                svc_name, asset_name, event_name))
                        try:
                            audit = AuditLogger(storage_client)
                            audit_details = {'asset': asset_name, 'service': svc_name, 'event': audit_event_name}
                            await audit.information('ASTDP', audit_details)
                        except:
                            _logger.warning("Failed to log the audit entry for {} deprecation.".format(asset_name))
                            pass
                    else:
                        raise StorageServerError
                else:
                    raise KeyError('{} asset record already deprecated.'.format(asset_name))
            else:
                raise ValueError('No record found in asset tracker for given service: {} asset: {} event: {}'.format(
                    svc_name, asset_name, event_name))
        else:
            raise StorageServerError
    except StorageServerError as err:
        msg = err.error
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": "Storage error: {}".format(msg)}))
    except KeyError as err:
        msg = str(err)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        _logger.error("Deprecate {} asset entry failed for {} service with {} event. {}".format(
            asset_name, svc_name, event_name, msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        msg = "For {} event, {} asset record entry has been deprecated.".format(event_name, asset_name)
        _logger.info(msg)
        return web.json_response({'success': msg})


async def get_datapoint_usage(request: web.Request) -> web.Response:
    """
    Args:
        request: a GET request to the /fledge/track/storage/assets Endpoint.

    Returns:
            A JSON response. An example would be.
            {
              "count" : 5,
               "assets" : [
                            {
                              "asset" : "sinusoid",
                              "datapoints" : [ "sinusoid" ]
                            },
                            {
                               "asset" : "motor",
                               "datapoints" : [ "rpm", "current", "voltage", "temperature" ]
                            }
                          ]
            }

    :Example:
            curl -sX GET http://localhost:8081/fledge/track/storage/assets

    """

    response = {"count": 0,
                "assets": []
                }
    try:
        storage_client = connect.get_storage_async()
        q_payload = PayloadBuilder().SELECT(). \
            DISTINCT(["asset", "data"]). \
            WHERE(["event", "=", "store"]). \
            payload()

        results = await storage_client.query_tbl_with_payload('asset_tracker', q_payload)

        total_datapoints = 0
        asset_info_list = []
        for row in results["rows"]:
            # The no of datapoints for this asset.
            asset_name = row["asset"]
            # Construct a dict that contains information about a single asset.
            current_count = int(row["data"]["count"])
            dict_to_add = {"asset": row["asset"], "datapoints": row["data"]["datapoints"], 'count': current_count}
            # appending information of single asset to the asset information list.

            # now find that this is a new asset or not.
            # Initialize index_of_found_asset by -1 . -1 means not found.
            index_of_found_asset = -1
            for (idx, asset_info) in enumerate(asset_info_list):
                if 'asset' in asset_info and asset_info['asset'] == asset_name:
                    index_of_found_asset = idx

            if index_of_found_asset != -1:
                # If current data point count exceed the maximum data point then replace
                # this new data point information else do nothing
                if current_count >= asset_info_list[index_of_found_asset]['count']:
                    asset_info_list.pop(index_of_found_asset)
                    asset_info_list.append(dict_to_add)
            else:
                # This is a new asset simply add to list.
                asset_info_list.append(dict_to_add)

        # finally calculate the total data points
        for asset_info in asset_info_list:
            total_datapoints += int(asset_info['count'])

        # Remove count for each asset_info
        for ast_info in asset_info_list:
            ast_info.pop('count')

        # update the required information.
        response['assets'] = asset_info_list
        response["count"] = total_datapoints

    except KeyError as msg:
        raise web.HTTPBadRequest(reason=str(msg), body=json.dumps({"message": str(msg)}))
    except TypeError as ex:
        raise web.HTTPBadRequest(reason=str(ex), body=json.dumps({"message": str(ex)}))
    except StorageServerError as ex:
        err_response = ex.error
        raise web.HTTPBadRequest(reason=err_response, body=json.dumps({"message": err_response}))
    except Exception as ex:
        msg = str(ex)
        _logger.error("Failed to get asset tracker store datapoints. {}".format(msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response(response)
