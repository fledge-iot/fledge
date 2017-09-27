# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Backup and Restore Rest API support"""

from aiohttp import web
# TODO: remove this and call actual class methods
from unittest.mock import MagicMock
Backup = MagicMock()

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    -----------------------------------------------------------------------------------
    | GET, POST       | /foglamp/backup                                                |
    | GET             | /foglamp/backup/{backup-id}                                    |
    | DELETE          | /foglamp/backup/{backup-id}                                    |
    |                                                                                  |
    | PUT             | /foglamp/backup/{backup-id}/restore                            |
    -----------------------------------------------------------------------------------
"""

async def get_backups(request):
    """
    Returns a list of all backups

    :Example: curl -X GET  http://localhost:8082/foglamp/backup
    :Example: curl -X GET  http://localhost:8082/foglamp/backup?limit=2&skip=1&status=complete
    """
    try:
        limit = int(request.query['limit']) if 'limit' in request.query else None
        skip = int(request.query['skip']) if 'skip' in request.query else None
        status = request.query['status'] if 'status' in request.query else None
        # TODO : Fix after actual implementation
        Backup.get_backup_list.return_value = [{'id': 28, 'date': '2017-08-30 04:05:10.382', 'status': 'running'},
                                               {'id': 27, 'date': '2017-08-29 04:05:13.392', 'status': 'failed'},
                                               {'id': 26, 'date': '2017-08-28 04:05:08.201', 'status': 'complete'}]

        # backup_json = [{"id": b[0], "date": b[1], "status": b[2]}
        #                for b in Backup.get_backup_list(limit=limit, skip=skip, status=status)]
        backup_json = Backup.get_backup_list(limit=limit, skip=skip, status=status)
    except Backup.DoesNotExist:
        raise web.HTTPNotFound(reason='No backups found for queried parameters')
    return web.json_response({"backups": backup_json})

async def create_backup(request):
    """
    Creates a backup

    :Example: curl -X POST http://localhost:8082/foglamp/backup
    """
    # TODO : Fix after actual implementation
    Backup.create_backup.return_value = "running"
    status = Backup.create_backup()
    return web.json_response({"status": status})

async def get_backup_details(request):
    """
    Returns the details of a backup

    :Example: curl -X GET  http://localhost:8082/foglamp/backup/1
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
        Backup.get_backup_details.return_value = \
            {"date": '2017-08-30 04:05:10.382', "status": "running"}
    except Backup.DoesNotExist:
        raise web.HTTPNotFound(reason='Backup with {} does not exist'.format(backup_id))

    _resp = Backup.get_backup_details(id=backup_id)
    _resp["id"] = backup_id
    return web.json_response(_resp)

async def delete_backup(request):
    """
    Delete a backup

    :Example: curl -X DELETE  http://localhost:8082/foglamp/backup/1
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
            Backup.delete_backup.return_value = "Backup deleted successfully"
        except Backup.DoesNotExist:
            raise web.HTTPNotFound(reason='Backup with {} does not exist'.format(backup_id))

        _resp = Backup.delete_backup(id=backup_id)
        return web.json_response({'message': _resp})

async def restore_backup(request):
    """
    Restore from a backup

    :Example: curl -X PUT  http://localhost:8082/foglamp/backup/1/restore
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
            Backup.restore_backup.return_value = 1
        except Backup.DoesNotExist:
            raise web.HTTPNotFound(reason='Backup with {} does not exist'.format(backup_id))
        try:
            Backup.restore_backup(id=backup_id)
            return web.json_response({'message': 'Restore backup with id {} started successfully'.format(backup_id)})
        except Backup.RestoreFailed as ex:
            return web.json_response({'error': 'Restore backup with id {} failed, reason {}'.format(backup_id, ex)})
