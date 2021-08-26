# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Backup and Restore Rest API support"""
import logging
import os
import sys
import tarfile
import json
from pathlib import Path
from aiohttp import web
from enum import IntEnum
from collections import OrderedDict

from fledge.common import logger
from fledge.common.audit_logger import AuditLogger
from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_DATA
from fledge.common.storage_client import payload_builder
from fledge.plugins.storage.common import exceptions
from fledge.services.core import connect

if 'fledge.plugins.storage.common.backup' not in sys.modules:
    from fledge.plugins.storage.common.backup import Backup

if 'fledge.plugins.storage.common.restore' not in sys.modules:
    from fledge.plugins.storage.common.restore import Restore

__author__ = "Vaibhav Singhal, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__DEFAULT_LIMIT = 20
__DEFAULT_OFFSET = 0

_help = """
    -----------------------------------------------------------------------------------
    | GET, POST       | /fledge/backup                                                |
    | POST            | /fledge/backup/upload                                         |
    | GET, DELETE     | /fledge/backup/{backup-id}                                    |
    | GET             | /fledge/backup/{backup-id}/download                           |
    | PUT             | /fledge/backup/{backup-id}/restore                            |
    | GET             | /fledge/backup/status                                         |
    -----------------------------------------------------------------------------------
"""

_logger = logger.setup(__name__, level=logging.INFO)


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

    :Example: curl -X GET http://localhost:8081/fledge/backup
    :Example: curl -X GET http://localhost:8081/fledge/backup?limit=2&skip=1&status=completed
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
        backup = Backup(connect.get_storage_async())
        backup_json = await backup.get_all_backups(limit=limit, skip=skip, status=status)

        res = []
        for row in backup_json:
            r = OrderedDict()
            r["id"] = row["id"]
            r["date"] = row["ts"]
            r["status"] = _get_status(int(row["status"]))
            res.append(r)

    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))

    return web.json_response({"backups": res})


async def create_backup(request):
    """ Creates a backup

    :Example: curl -X POST http://localhost:8081/fledge/backup
    """
    try:
        backup = Backup(connect.get_storage_async())
        status = await backup.create_backup()
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))

    return web.json_response({"status": status})


async def get_backup_details(request):
    """ Returns the details of a backup

    :Example: curl -X GET http://localhost:8081/fledge/backup/1
    """
    backup_id = request.match_info.get('backup_id', None)
    try:
        backup_id = int(backup_id)
        backup = Backup(connect.get_storage_async())
        backup_json = await backup.get_backup_details(backup_id)

        resp = {"status": _get_status(int(backup_json["status"])),
                'id': backup_json["id"],
                'date': backup_json["ts"]
                }

    except ValueError:
        raise web.HTTPBadRequest(reason='Invalid backup id')
    except exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason='Backup id {} does not exist'.format(backup_id))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=(str(ex)))

    return web.json_response(resp)


async def get_backup_download(request):
    """ Download back up file by id

    :Example:
        wget -O fledge-backup-1.tar.gz http://localhost:8081/fledge/backup/1/download

    """
    backup_id = request.match_info.get('backup_id', None)
    try:
        backup_id = int(backup_id)
        backup = Backup(connect.get_storage_async())
        backup_json = await backup.get_backup_details(backup_id)

        # Strip filename from backup path
        file_name_path = str(backup_json["file_name"]).split('data/backup/')
        file_name = str(file_name_path[1])
        dir_name = _FLEDGE_DATA + '/backup/' if _FLEDGE_DATA else _FLEDGE_ROOT + "/data/backup/"
        source = dir_name + file_name

        # Create tar file
        t = tarfile.open(source + ".tar.gz", "w:gz")
        t.add(source, arcname=os.path.basename(source))
        t.close()

        # Path of tar.gz file
        gz_path = Path(source + ".tar.gz")

    except ValueError:
        raise web.HTTPBadRequest(reason='Invalid backup id')
    except exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason='Backup id {} does not exist'.format(backup_id))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=(str(ex)))

    return web.FileResponse(path=gz_path)


async def delete_backup(request):
    """ Delete a backup

    :Example: curl -X DELETE http://localhost:8081/fledge/backup/1
    """
    backup_id = request.match_info.get('backup_id', None)
    try:
        backup_id = int(backup_id)
        backup = Backup(connect.get_storage_async())
        await backup.delete_backup(backup_id)
        return web.json_response({'message': "Backup deleted successfully"})
    except ValueError:
        raise web.HTTPBadRequest(reason='Invalid backup id')
    except exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason='Backup id {} does not exist'.format(backup_id))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))


async def restore_backup(request):
    """
    Restore from a backup
    :Example: curl -X PUT http://localhost:8081/fledge/backup/1/restore
    """

    # TODO: FOGL-861
    backup_id = request.match_info.get('backup_id', None)
    try:
        backup_id = int(backup_id)
        restore = Restore(connect.get_storage_async())
        status = await restore.restore_backup(backup_id)
        return web.json_response({'status': status})
    except ValueError:
        raise web.HTTPBadRequest(reason='Invalid backup id')
    except exceptions.DoesNotExist:
        raise web.HTTPNotFound(reason='Backup with {} does not exist'.format(backup_id))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))


async def get_backup_status(request):
    """

    Returns:
           an array of backup status enumeration key index values

    :Example:

        curl -X GET http://localhost:8081/fledge/backup/status
    """
    results = []
    for _status in Status:
        data = {'index': _status.value, 'name': _status.name}
        results.append(data)

    return web.json_response({"backupStatus": results})


async def upload_backup(request):
    try:
        fl_data_path = _FLEDGE_DATA if _FLEDGE_DATA else _FLEDGE_ROOT + '/data'
        backup_prefix = "fledge_backup_"
        backup_path = "{}/backup".format(fl_data_path)
        temp_path = "{}/upload".format(fl_data_path)
        data = await request.post()
        file_param = data.get('filename')
        file_name = file_param.filename
        if not str(file_name).endswith(".tar.gz"):
            raise NameError("{} file does not have with tar gzip.".format(file_name))
        if not str(file_name).startswith(backup_prefix):
            raise NameError("{} backup filename is invalid. Please either check file format from FLEDGE_DATA/backup "
                            "or create it from GUI create new backup from Backup & Restore option".format(file_name))
        # Create temporary directory for tar extraction & backup data directory for Fledge
        cmd = "mkdir -p {} {}".format(temp_path, backup_path)
        os.system(cmd)
        file_data = file_param.file
        # Extract tar inside temporary directory
        tar_file = tarfile.open(fileobj=file_data, mode='r:*')
        tar_file_names = tar_file.getnames()
        valid_extensions = ('.db', '.dump')
        if any((item.startswith(backup_prefix) and item.endswith(valid_extensions)) for item in tar_file_names):
            tar_file.extractall(temp_path)
            source = "{}/{}".format(temp_path, tar_file_names[0])
            cmd = "cp {} {}".format(source, backup_path)
            ret_code = os.system(cmd)
            if ret_code != 0:
                raise OSError("{} upload failed during copy to {}".format(file_name, backup_path))
            else:
                # TODO: ts as per post param if given in payload
                # insert backup record entry in db
                full_file_name_path = "{}/{}".format(backup_path, tar_file_names[0])
                payload = payload_builder.PayloadBuilder().INSERT(
                    file_name=full_file_name_path, ts="now()", type=1, status=2, exit_code=0).payload()
                # audit trail entry
                storage = connect.get_storage_async()
                await storage.insert_into_tbl("backups", payload)
                audit = AuditLogger(storage)
                await audit.information('BKEXC', {'status': 'completed', 'message': 'From upload backup'})
                # TODO: FOGL-4239 - readings table upload
        else:
            raise NameError('Either {} prefix or {} suffix not found in given {} tar file'.format(
                backup_prefix, file_name, valid_extensions))
    except (NameError, OSError, RuntimeError) as err_msg:
        msg = str(err_msg)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err_msg:
        msg = str(err_msg)
        raise web.HTTPNotImplemented(reason=msg, body=json.dumps({"message": msg}))
    except Exception as exc:
        msg = str(exc)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        msg = "{} backup uploaded successfully.".format(file_name)
        return web.json_response({"message": msg})
    finally:
        # Remove temporary directory
        cmd = "rm -rf {}".format(temp_path)
        os.system(cmd)
