# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from aiohttp import web

from fledge.common.logger import FLCoreLogger
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core import connect

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2023, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ----------------------------------------------------------------
    | GET  DELETE          | /fledge/monitors                      |
    | GET  DELETE          | /fledge/monitors/{service}            |
    | GET  DELETE          | /fledge/monitors/{service}/{counter}  |
    ----------------------------------------------------------------
"""
_LOGGER = FLCoreLogger().get_logger(__name__)

def setup(app):
    app.router.add_route('GET', '/fledge/monitors', get_all)
    app.router.add_route('GET', '/fledge/monitors/{service}', get_by_service_name)
    app.router.add_route('GET', '/fledge/monitors/{service}/{counter}', get_by_service_and_counter_name)
    app.router.add_route('DELETE', '/fledge/monitors', purge_all)
    app.router.add_route('DELETE', '/fledge/monitors/{service}', purge_by_service)
    app.router.add_route('DELETE', '/fledge/monitors/{service}/{counter}', purge_by_service_and_counter)

async def get_all(request: web.Request) -> web.Response:
    """ GET list of performance monitors

    :Example:
        curl -sX GET http://localhost:8081/fledge/monitors
    """
    return web.json_response({"message": "To be Implemented"})


async def get_by_service_name(request: web.Request) -> web.Response:
    """ GET performance monitors for the given service

    :Example:
        curl -sX GET http://localhost:8081/fledge/monitors/<SVC_NAME>
    """
    service = request.match_info.get('service', None)
    storage = connect.get_storage_async()
    payload = PayloadBuilder().SELECT("average", "maximum", "minimum", "monitor", "samples", "ts").ALIAS(
        "return", ("ts", 'timestamp')).FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")).WHERE(
        ["service", '=', service]).payload()
    response = {"service": service}
    result = await storage.query_tbl_with_payload('monitors', payload)
    if 'rows' in result:
        monitor = {}
        for d in result["rows"]:
            val = {"average": d["average"], "maximum": d["maximum"], "minimum": d["minimum"], "samples": d["samples"],
                   "timestamp": d["timestamp"]}
            monitor.setdefault(d['monitor'], []).append(val)
        monitors = [{'monitor': k, 'values': v} for k, v in monitor.items()]
        response["monitors"] = monitors
    return web.json_response(response)

async def get_by_service_and_counter_name(request: web.Request) -> web.Response:
    """ GET values for the single counter for the single service

    :Example:
        curl -sX GET http://localhost:8081/fledge/monitors/<SVC_NAME>/<COUNTER_NAME>
    """
    service = request.match_info.get('service', None)
    counter = request.match_info.get('counter', None)

    storage = connect.get_storage_async()
    payload = PayloadBuilder().SELECT("average", "maximum", "minimum", "samples", "ts").ALIAS(
        "return", ("ts", 'timestamp')).FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")).WHERE(
        ["service", '=', service]).AND_WHERE(["monitor", '=', counter]).payload()
    result = await storage.query_tbl_with_payload('monitors', payload)
    response = {}
    if 'rows' in result:
        response = {"service": service, "monitors":{"monitor": counter}}
        response["monitors"]["values"] = result["rows"] if result["rows"] else []
    return web.json_response(response)

async def purge_all(request: web.Request) -> web.Response:
    """ DELETE all performance monitors

    :Example:
        curl -sX DELETE http://localhost:8081/fledge/monitors
    """
    storage = connect.get_storage_async()
    result = await storage.delete_from_tbl("monitors", {})
    message = "Nothing to remove for service performance counters."
    if 'rows_affected' in result:
        if result['response'] == "deleted" and result['rows_affected']:
            message = "All Performance counters have been removed successfully."
    return web.json_response({"message": message})

async def purge_by_service(request: web.Request) -> web.Response:
    """ DELETE performance monitors for the given service

    :Example:
        curl -sX DELETE http://localhost:8081/fledge/monitors/<SVC_NAME>
    """
    service = request.match_info.get('service', None)
    storage = connect.get_storage_async()
    payload = PayloadBuilder().WHERE(["service", '=', service]).payload()
    result = await storage.delete_from_tbl("monitors", payload)
    message = "Nothing to remove counters from '{}' service.".format(service)
    if 'rows_affected' in result:
        if result['response'] == "deleted" and result['rows_affected']:
            message = "Performance counters have been removed from '{}' service.".format(service)
    return web.json_response({"message": message})

async def purge_by_service_and_counter(request: web.Request) -> web.Response:
    """ DELETE performance monitors for the single counter for the single service

    :Example:
        curl -sX DELETE http://localhost:8081/fledge/monitors/<SVC_NAME>/<COUNTER_NAME>
    """
    service = request.match_info.get('service', None)
    counter = request.match_info.get('counter', None)
    storage = connect.get_storage_async()
    payload = PayloadBuilder().WHERE(["service", '=', service]).AND_WHERE(
        ["monitor", '=', counter]).payload()
    result = await storage.delete_from_tbl("monitors", payload)
    message = "Nothing to remove '{}' counter from '{}' service.".format(counter, service)
    if 'rows_affected' in result:
        if result['response'] == "deleted" and result['rows_affected']:
            message = "Performance '{}' counter has been removed from '{}' service.".format(counter, service)
    return web.json_response({"message": message})
