# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END


import os
from aiohttp import web
from fledge.services.core.snapshot import SnapshotPluginBuilder
from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_DATA
from fledge.common.web.middleware import has_permission

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    -------------------------------------------------------------------------
    | GET POST        | /fledge/snapshot/plugins                            |
    | PUT DELETE      | /fledge/snapshot/plugins/{id}                       |
    -------------------------------------------------------------------------
"""


@has_permission("admin")
async def get_snapshot(request):
    """ get list of available snapshots

    :Example:
        curl -X GET http://localhost:8081/fledge/snapshot/plugins

        When auth is mandatory:
        curl -X GET http://localhost:8081/fledge/snapshot/plugins -H "authorization: <token>" 
    """
    # Get snapshot directory path
    snapshot_dir = _get_snapshot_dir()
    valid_extension = '.tar.gz'
    sorted_list = []
    if os.path.isdir(snapshot_dir):
        for root, dirs, files in os.walk(snapshot_dir):
            valid_files = list(
                filter(lambda f: f.endswith(valid_extension), files))
            list_files = list(map(
                lambda x: {"id": x.split("snapshot-plugin-")[1].split(".tar.gz")[0],
                           "name": x}, valid_files))
            sorted_list = sorted(list_files, key=lambda k: k['id'], reverse=True)

    return web.json_response({"snapshots": sorted_list})


@has_permission("admin")
async def post_snapshot(request):
    """ Create a snapshot  by name

    :Example:
        curl -X POST http://localhost:8081/fledge/snapshot/plugins

        When auth is mandatory:
        curl -X POST http://localhost:8081/fledge/snapshot/plugins -H "authorization: <token>" 
    """
    try:
        snapshot_dir = _get_snapshot_dir()
        snapshot_id, snapshot_name = await SnapshotPluginBuilder(
            snapshot_dir).build()
    except Exception as ex:
        raise web.HTTPInternalServerError(
            reason='Snapshot could not be created. {}'.format(str(ex)))
    else:
        return web.json_response({
            "message": "snapshot id={}, file={} created successfully.".format(
                snapshot_id, snapshot_name)})


@has_permission("admin")
async def put_snapshot(request):
    """extract a snapshot

    :Example:
        curl -X PUT http://localhost:8081/fledge/snapshot/plugins/1554204238

        When auth is mandatory:
        curl -X PUT http://localhost:8081/fledge/snapshot/plugins/1554204238 -H "authorization: <token>" 
    """
    try:
        snapshot_id = request.match_info.get('id', None)
        snapshot_name = "snapshot-plugin-{}.tar.gz".format(snapshot_id)

        try:
            snapshot_id = int(snapshot_id)
        except:
            raise ValueError('Invalid snapshot id: {}'.format(snapshot_id))

        if not os.path.isdir(_get_snapshot_dir()):
            raise web.HTTPNotFound(reason="No snapshot found.")

        snapshot_dir = _get_snapshot_dir()
        for root, dirs, files in os.walk(snapshot_dir):
            if str(snapshot_name) not in files:
                raise web.HTTPNotFound(reason='{} not found'.format(snapshot_name))

        p = "{}/{}".format(snapshot_dir, snapshot_name)
        SnapshotPluginBuilder(snapshot_dir).extract_files(p)
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(
            reason='Snapshot {} could not be restored. {}'.format(snapshot_name,
                                                                  str(ex)))
    else:
        return web.json_response(
            {"message": "snapshot {} restored successfully.".format(
                snapshot_name)})


@has_permission("admin")
async def delete_snapshot(request):
    """delete a snapshot

    :Example:
        curl -X DELETE http://localhost:8081/fledge/snapshot/plugins/1554204238

        When auth is mandatory:
        curl -X DELETE http://localhost:8081/fledge/snapshot/plugins/1554204238 -H "authorization: <token>" 
    """
    try:
        snapshot_id = request.match_info.get('id', None)
        snapshot_name = "snapshot-plugin-{}.tar.gz".format(snapshot_id)

        try:
            snapshot_id = int(snapshot_id)
        except:
            raise ValueError('Invalid snapshot id: {}'.format(snapshot_id))

        if not os.path.isdir(_get_snapshot_dir()):
            raise web.HTTPNotFound(reason="No snapshot found.")

        snapshot_dir = _get_snapshot_dir()
        for root, dirs, files in os.walk(_get_snapshot_dir()):
            if str(snapshot_name) not in files:
                raise web.HTTPNotFound(reason='{} not found'.format(snapshot_name))

        p = "{}/{}".format(snapshot_dir, snapshot_name)
        os.remove(p)
    except ValueError as ex:
        raise web.HTTPBadRequest(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(
            reason='Snapshot {} could not be deleted. {}'.format(snapshot_name,
                                                                 str(ex)))
    else:
        return web.json_response(
            {"message": "snapshot {} deleted successfully.".format(
                snapshot_name)})


def _get_snapshot_dir():
    if _FLEDGE_DATA:
        snapshot_dir = os.path.expanduser(_FLEDGE_DATA + '/snapshots/plugins')
    else:
        snapshot_dir = os.path.expanduser(
            _FLEDGE_ROOT + '/data/snapshots/plugins')
    return snapshot_dir
