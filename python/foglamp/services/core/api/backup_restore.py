# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Backup and Restore Rest API support"""

from aiohttp import web
from enum import IntEnum

from foglamp.services.core import connect
from foglamp.plugins.storage.postgres.backup_restore.backup_postgres import Backup
import foglamp.plugins.storage.postgres.backup_restore.exceptions as exceptions

# TODO: remove this and call actual class methods
from unittest.mock import MagicMock
Backup_Mock = MagicMock()


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    -----------------------------------------------------------------------------------
    | GET, POST       | /foglamp/backup                                                |
    | GET, DELETE     | /foglamp/backup/{backup-id}                                    |
    | PUT             | /foglamp/backup/{backup-id}/restore                            |
    -----------------------------------------------------------------------------------
"""


class Status(IntEnum):
    """Enumeration for backup.status"""
    running = 1
    completed = 2
    cancelled = 3
    interrupted = 4
    failed = 5
    restored = 6


async def get_backups(request):
    """
    Returns a list of all backups

    :Example: curl -X GET http://localhost:8081/foglamp/backup
    :Example: curl -X GET http://localhost:8081/foglamp/backup?limit=2&skip=1&status=completed
    """
    backup = Backup(connect.get_storage())
    try:
        limit = int(request.query['limit']) if 'limit' in request.query else None
        skip = int(request.query['skip']) if 'skip' in request.query else None
        status = request.query['status'] if 'status' in request.query else None
        backup_json = backup.get_all_backups(limit=limit, skip=skip, status=Status[status].value)
    except exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason='No backups found for queried parameters')
    return web.json_response({"backups": backup_json})

async def create_backup(request):
    """
    Creates a backup

    :Example: curl -X POST http://localhost:8081/foglamp/backup
    """
    backup = Backup(connect.get_storage())
    status = await backup.create_backup()
    return web.json_response({"status": status})

async def get_backup_details(request):
    """
    Returns the details of a backup

    :Example: curl -X GET http://localhost:8081/foglamp/backup/1
    """
    backup_id = request.match_info.get('backup_id', None)
    backup = Backup(connect.get_storage())
    if not backup_id:
        raise web.HTTPBadRequest(reason='Backup id is required')
    else:
        try:
            backup_id = int(backup_id)
        except ValueError:
            raise web.HTTPBadRequest(reason='Invalid backup id')
    try:
        _resp = backup.get_backup_details(backup_id)
        _resp["id"] = backup_id
        return web.json_response(_resp)
    except exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason='Backup with {} does not exist'.format(backup_id))


async def delete_backup(request):
    """
    Delete a backup

    :Example: curl -X DELETE http://localhost:8081/foglamp/backup/1
    """
    backup_id = request.match_info.get('backup_id', None)
    backup = Backup(connect.get_storage())
    if not backup_id:
        raise web.HTTPBadRequest(reason='Backup id is required')
    else:
        try:
            backup_id = int(backup_id)
        except ValueError:
            raise web.HTTPBadRequest(reason='Invalid backup id')
        try:
            backup.delete_backup(backup_id)
            return web.json_response({'message': "Backup deleted successfully"})
        except exceptions.DoesNotExist:
            raise web.HTTPNotFound(reason='Backup with {} does not exist'.format(backup_id))

async def restore_backup(request):
    """
    Restore from a backup

    :Example: curl -X PUT http://localhost:8081/foglamp/backup/1/restore
    """
    backup_id = request.match_info.get('backup_id', None)
    if not backup_id:
        raise web.HTTPBadRequest(reason='Backup id is required')
    else:
        try:
            backup_id = int(backup_id)
        except ValueError:
            raise web.HTTPBadRequest(reason='Invalid backup id')
        try:
            # TODO : Fix after actual implementation
            Backup_Mock.restore_backup.return_value = 1
        except Backup_Mock.DoesNotExist:
            raise web.HTTPNotFound(reason='Backup with {} does not exist'.format(backup_id))
        try:
            Backup_Mock.restore_backup(id=backup_id)
            return web.json_response({'message': 'Restore backup with id {} started successfully'.format(backup_id)})
        except Backup_Mock.RestoreFailed as ex:
            return web.json_response({'error': 'Restore backup with id {} failed, reason {}'.format(backup_id, ex)})
