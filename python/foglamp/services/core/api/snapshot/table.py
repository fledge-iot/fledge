# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


import json
from aiohttp import web

from foglamp.services.core.connect import *
from foglamp.common.storage_client.exceptions import StorageServerError
from foglamp.common.web.middleware import has_permission


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    -------------------------------------------------------------------------------
    | GET POST        | /foglamp/snapshot/category                                |
    | PUT DELETE      | /foglamp/snapshot/category/{id}                           |
    | GET POST        | /foglamp/snapshot/schedule                                |
    | PUT DELETE      | /foglamp/snapshot/schedule/{id}                           |
    -------------------------------------------------------------------------------
"""

_tables = {
    "category": "configuration",
    "schedule": "schedules"
}


@has_permission("admin")
async def get_snapshot(request):
    """ get list of available snapshots

    :Example:
        curl -X GET http://localhost:8081/foglamp/snapshot/category
        curl -X GET http://localhost:8081/foglamp/snapshot/schedule
        
        When auth is mandatory:
        curl -X GET http://localhost:8081/foglamp/snapshot/category -H "authorization: <token>"
        curl -X GET http://localhost:8081/foglamp/snapshot/schedule -H "authorization: <token>"
    """
    try:
        r_path = request.path.split('/foglamp/snapshot/')
        table = _tables[r_path[1]]

        _storage = get_storage_async()  # from foglamp.services.core.connect
        retval = await _storage.get_snapshot(table)
        newlist = sorted(retval["rows"], key=lambda k: k['id'], reverse=True)
    except (StorageServerError, Exception) as ex:
        raise web.HTTPInternalServerError(reason='{} table snapshots could not be fetched. {}'.format(table, str(ex)))
    else:
        return web.json_response({"snapshots": newlist})


@has_permission("admin")
async def post_snapshot(request):
    """ Create a snapshot

    :Example:
        curl -X POST http://localhost:8081/foglamp/snapshot/category
        curl -X POST http://localhost:8081/foglamp/snapshot/schedule
        
        When auth is mandatory:
        curl -X POST http://localhost:8081/foglamp/snapshot/category -H "authorization: <token>"
        curl -X POST http://localhost:8081/foglamp/snapshot/schedule -H "authorization: <token>"
    """
    try:
        r_path = request.path.split('/foglamp/snapshot/')
        table = _tables[r_path[1]]

        _storage = get_storage_async()  # from foglamp.services.core.connect
        retval = await _storage.post_snapshot(table)
    except (StorageServerError, Exception) as ex:
        raise web.HTTPInternalServerError(reason='{} table snapshot could not be created. {}'.format(table, str(ex)))
    else:
        return web.json_response(retval["created"])


@has_permission("admin")
async def put_snapshot(request):
    """restore a snapshot

    :Example:
        curl -X PUT http://localhost:8081/foglamp/snapshot/category/1554202741
        curl -X PUT http://localhost:8081/foglamp/snapshot/schedule/1554202742
        
        When auth is mandatory:
        curl -X PUT http://localhost:8081/foglamp/snapshot/category/1554202741 -H "authorization: <token>"
        curl -X PUT http://localhost:8081/foglamp/snapshot/schedule/1554202742 -H "authorization: <token>"
    """
    try:
        r_path = request.path.split('/foglamp/snapshot/')
        table = _tables[r_path[1].split('/')[0]]

        snapshot_id = request.match_info.get('id', None)

        try:
            snapshot_id = int(snapshot_id)
        except:
            raise ValueError('Invalid snapshot id: {}'.format(snapshot_id))

        _storage = get_storage_async()  # from foglamp.services.core.connect
        retval = await _storage.put_snapshot(table, snapshot_id)
    except StorageServerError as ex:
        if int(ex.code) in range(400, 500):
            raise web.HTTPBadRequest(
                reason='{} table snapshot could not be restored. {}'.format(table, json.loads(ex.error)['message']))
        else:
            raise web.HTTPInternalServerError(
                reason='{} table snapshot could not be restored. {}'.format(table, json.loads(ex.error)['message']))
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='{} table snapshot could not be restored. {}'.format(table, str(ex)))
    else:
        return web.json_response(retval["loaded"])


@has_permission("admin")
async def delete_snapshot(request):
    """delete a snapshot

    :Example:
        curl -X DELETE http://localhost:8081/foglamp/snapshot/category/1554202741
        curl -X DELETE http://localhost:8081/foglamp/snapshot/schedule/1554202742
        
        When auth is mandatory:
        curl -X DELETE http://localhost:8081/foglamp/snapshot/category/1554202741 -H "authorization: <token>"
        curl -X DELETE http://localhost:8081/foglamp/snapshot/schedule/1554202742 -H "authorization: <token>"
    """
    try:
        r_path = request.path.split('/foglamp/snapshot/')
        table = _tables[r_path[1].split('/')[0]]

        snapshot_id = request.match_info.get('id', None)
        try:
            snapshot_id = int(snapshot_id)
        except:
            raise ValueError('Invalid snapshot id: {}'.format(snapshot_id))

        _storage = get_storage_async()  # from foglamp.services.core.connect
        retval = await _storage.delete_snapshot(table, snapshot_id)
    except StorageServerError as ex:
        if int(ex.code) in range(400, 500):
            raise web.HTTPBadRequest(
                reason='{} table snapshot could not be deleted. {}'.format(table, json.loads(ex.error)['message']))
        else:
            raise web.HTTPInternalServerError(
                reason='{} table snapshot could not be deleted. {}'.format(table, json.loads(ex.error)['message']))
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='{} table snapshot could not be deleted. {}'.format(table, str(ex)))
    else:
        return web.json_response(retval["deleted"])
