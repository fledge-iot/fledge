# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Backup and Restore Rest API support"""

from aiohttp import web
from enum import IntEnum
from collections import OrderedDict

from foglamp.services.core import connect
from foglamp.plugins.storage.postgres.backup_restore.backup_postgres import Backup
from foglamp.plugins.storage.postgres.backup_restore.restore_postgres import Restore
from foglamp.plugins.storage.postgres.backup_restore import exceptions


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__DEFAULT_LIMIT = 20
__DEFAULT_OFFSET = 0

_help = """
    ------------------------------------------------------------------------------------
    | GET, POST       | /foglamp/backup                                                |
    | GET, DELETE     | /foglamp/backup/{backup-id}                                    |
    | PUT             | /foglamp/backup/{backup-id}/restore                            |
    | GET             | /foglamp/backup/status                                         |
    ------------------------------------------------------------------------------------
"""


class Status(IntEnum):
    """Enumeration for backup.status"""
    RUNNING = 1
    COMPLETED = 2
    CANCELED = 3
    INTERRUPTED = 4
    FAILED = 5
    RESTORED = 6


def _get_status(status_code):
    if status_code not in range(1, 7):
        return "UNKNOWN"
    return Status(status_code).name


async def get_backups(request):
    """ Returns a list of all backups

    :Example: curl -X GET http://localhost:8081/foglamp/backup
    :Example: curl -X GET http://localhost:8081/foglamp/backup?limit=2&skip=1&status=completed
    """
    limit = __DEFAULT_LIMIT
    if 'limit' in request.query and request.query['limit'] != '':
        try:
            limit = int(request.query['limit'])
            if limit < 0:
                raise ValueError
        except ValueError:
            raise web.HTTPBadRequest(reason="Limit must be a positive integer")

    skip = __DEFAULT_OFFSET
    if 'skip' in request.query and request.query['skip'] != '':
        try:
            skip = int(request.query['skip'])
            if skip < 0:
                raise ValueError
        except ValueError:
            raise web.HTTPBadRequest(reason="Skip/Offset must be a positive integer")

    status = None
    if 'status' in request.query and request.query['status'] != '':
        try:
            status = Status[request.query['status'].upper()].value
        except KeyError as ex:
            raise web.HTTPBadRequest(reason="{} is not a valid status".format(ex))
    try:
        backup = Backup(connect.get_storage())
        backup_json = backup.get_all_backups(limit=limit, skip=skip, status=status)

        res = []
        for row in backup_json:
            r = OrderedDict()
            r["id"] = row["id"]
            r["date"] = row["ts"]
            r["status"] = _get_status(int(row["status"]))
            res.append(r)

    except Exception as ex:
        raise web.HTTPException(reason=str(ex))

    return web.json_response({"backups": res})


async def create_backup(request):
    """ Creates a backup

    :Example: curl -X POST http://localhost:8081/foglamp/backup
    """
    try:
        backup = Backup(connect.get_storage())
        status = await backup.create_backup()
    except Exception as ex:
        raise web.HTTPException(reason=str(ex))

    return web.json_response({"status": status})


async def get_backup_details(request):
    """ Returns the details of a backup

    :Example: curl -X GET http://localhost:8081/foglamp/backup/1
    """
    backup_id = request.match_info.get('backup_id', None)
    try:
        backup_id = int(backup_id)
        backup = Backup(connect.get_storage())
        backup_json = backup.get_backup_details(backup_id)

        resp = {"status": _get_status(int(backup_json["status"])),
                'id': backup_json["id"],
                'date': backup_json["ts"]
                }

    except ValueError:
        raise web.HTTPBadRequest(reason='Invalid backup id')
    except exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason='Backup id {} does not exist'.format(backup_id))
    except Exception as ex:
        raise web.HTTPException(reason=(str(ex)))

    return web.json_response(resp)


async def delete_backup(request):
    """ Delete a backup

    :Example: curl -X DELETE http://localhost:8081/foglamp/backup/1
    """
    backup_id = request.match_info.get('backup_id', None)
    try:
        backup_id = int(backup_id)
        backup = Backup(connect.get_storage())
        backup.delete_backup(backup_id)
        return web.json_response({'message': "Backup deleted successfully"})
    except ValueError:
        raise web.HTTPBadRequest(reason='Invalid backup id')
    except exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason='Backup id {} does not exist'.format(backup_id))
    except Exception as ex:
        raise web.HTTPException(reason=str(ex))


async def restore_backup(request):
    """
    Restore from a backup
    :Example: curl -X PUT http://localhost:8081/foglamp/backup/1/restore
    """

    # TODO: FOGL-861
    backup_id = request.match_info.get('backup_id', None)
    try:
        backup_id = int(backup_id)
        restore = Restore(connect.get_storage())
        status = await restore.restore_backup(backup_id)
        return web.json_response({'status': status})
    except ValueError:
        raise web.HTTPBadRequest(reason='Invalid backup id')
    except exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason='Backup with {} does not exist'.format(backup_id))
    except Exception as ex:
        raise web.HTTPException(reason=str(ex))


async def get_backup_status(request):
    """

    Returns:
           an array of backup status enumeration key index values

    :Example:

        curl -X GET http://localhost:8081/foglamp/backup/status
    """
    results = []
    for _status in Status:
        data = {'index': _status.value, 'name': _status.name}
        results.append(data)

    return web.json_response({"backupStatus": results})
