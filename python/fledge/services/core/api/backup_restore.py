# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Backup and Restore Rest API support"""
import os
import sys
import tarfile
import json
from pathlib import Path
from aiohttp import web
from enum import IntEnum
from collections import OrderedDict

from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_DATA
from fledge.common.audit_logger import AuditLogger
from fledge.common.logger import FLCoreLogger

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

_logger = FLCoreLogger().get_logger(__name__)


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

    :Example:
        curl -sX GET http://localhost:8081/fledge/backup
        curl -sX GET http://localhost:8081/fledge/backup?status=completed
        curl -sX GET http://localhost:8081/fledge/backup?limit=1
        curl -sX GET "http://localhost:8081/fledge/backup?limit=2&status=restored"
        curl -sX GET http://localhost:8081/fledge/backup?skip=1
        curl -sX GET "http://localhost:8081/fledge/backup?skip=1&limit=1"
        curl -sX GET "http://localhost:8081/fledge/backup?skip=1&status=completed"
        curl -sX GET "http://localhost:8081/fledge/backup?skip=1&status=completed&limit=2"
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
        msg = str(ex)
        _logger.error("Get all backups failed. {}".format(msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    return web.json_response({"backups": res})


async def create_backup(request):
    """ Creates a backup

    :Example: curl -X POST http://localhost:8081/fledge/backup
    """
    try:
        backup = Backup(connect.get_storage_async())
        status = await backup.create_backup()
    except Exception as ex:
        msg = str(ex)
        _logger.error("Failed to create Backup. {}".format(msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
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
        msg = str(ex)
        _logger.error("Failed to fetch backup details for ID: <{}>. {}".format(backup_id, msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
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
        if not os.path.isfile(source):
            raise FileNotFoundError('{} backup file does not exist in {} directory'.format(file_name, dir_name))
        # Find the source extension
        dummy, file_extension = os.path.splitext(source)
        # backward compatibility (<= 1.9.2)
        if file_extension in (".db", ".dump"):
            # Create tar file
            t = tarfile.open(source + ".tar.gz", "w:gz")
            t.add(source, arcname=os.path.basename(source))
            t.close()
            gz_path = Path(source + ".tar.gz")
        else:
            gz_path = Path(source)
        _logger.debug("get_backup_download - file_extension :{}: - gz_path :{}:".format(file_extension, gz_path))
    except FileNotFoundError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except ValueError:
        msg = "Invalid backup id"
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except exceptions.DoesNotExist:
        msg = "Backup id {} does not exist".format(backup_id)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        _logger.error("Failed to backup download for ID:<{}>. {}".format(backup_id, msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
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
        msg = str(ex)
        _logger.error("Failed to delete Backup ID:<{}>. {}".format(backup_id, msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))


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
        msg = str(ex)
        _logger.error("Failed to restore Backup ID:<{}>. {}".format(backup_id, msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))


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


async def upload_backup(request: web.Request) -> web.Response:
    """
    Upload a backup file

    :Example:
        curl -F "filename=@fledge_backup_2021_08_24_13_27_08.tar.gz" localhost:8081/fledge/backup/upload
        curl -F "filename=@fledge_backup_2021_08_25_16_37_01.dump.tar.gz" localhost:8081/fledge/backup/upload
    """

    try:
        fl_data_path = _FLEDGE_DATA if _FLEDGE_DATA else _FLEDGE_ROOT + '/data'
        backup_prefix = "fledge_backup_"
        backup_path = "{}/backup".format(fl_data_path)
        temp_path = "{}/upload".format(fl_data_path)
        valid_extensions = ('.db', '.dump')
        reader = await request.multipart()
        # reader.next() will `yield` the fields of your form
        field = await reader.next()
        file_name = field.filename
        if not str(file_name).endswith(".tar.gz"):
            raise NameError("{} file should end with .tar.gz extension".format(file_name))
        if not str(file_name).startswith(backup_prefix):
            raise NameError("{} filename is invalid. Either check file format from FLEDGE_DATA/backup "
                            "or create it from GUI create new backup from Backup & Restore option".format(file_name))
        # Create temporary directory for tar extraction & backup data directory for Fledge
        cmd = "mkdir -p {} {}".format(temp_path, backup_path)
        os.system(cmd)
        # You cannot rely on Content-Length if transfer is chunked
        size = 0
        with open("{}/{}".format(temp_path, file_name), 'wb') as temp_file:
            while True:
                chunk = await field.read_chunk()  # 8192 bytes by default.
                if not chunk:
                    break
                size += len(chunk)
                temp_file.write(chunk)

        _logger.debug("upload_backup - temp_path :{}: file_name :{}: ".format(temp_path, file_name))
        # Extract tar inside temporary directory
        tar_file = tarfile.open(name="{}/{}".format(temp_path, file_name), mode='r:*')
        tar_file_names = tar_file.getnames()
        if any((item.startswith(backup_prefix) and item.endswith(valid_extensions)) for item in tar_file_names):
            if any((item.startswith("etc") and item.endswith("etc")) for item in tar_file_names):
                source = temp_path + "/" + file_name
                backup_file_name = file_name
            # backward compatibility (<= 1.9.2)
            else:
                tar_file.extractall(temp_path)
                backup_file_name = tar_file_names[0]
                source = "{}/{}".format(temp_path, backup_file_name)
            cmd = "cp {} {}".format(source, backup_path)
            _logger.debug("upload_backup: source :{}: - cmd :{}: - filename :{}:".format(source, cmd, backup_file_name))
            ret_code = os.system(cmd)
            if ret_code != 0:
                raise OSError("{} upload failed during copy to path:{}".format(file_name, backup_path))
            # TODO: FOGL-5876 ts as per post param if given in payload
            # insert backup record entry in db
            full_file_name_path = "{}/{}".format(backup_path, backup_file_name)
            payload = payload_builder.PayloadBuilder().INSERT(
                file_name=full_file_name_path, ts="now()", type=1, status=2, exit_code=0).payload()
            # audit trail entry
            storage = connect.get_storage_async()
            await storage.insert_into_tbl("backups", payload)
            audit = AuditLogger(storage)
            await audit.information('BKEXC', {'status': 'completed', 'message': 'From upload backup'})
            # TODO: FOGL-4239 - readings table upload
        else:
            raise NameError('Either {} prefix or {} valid extension is not found inside given tar file'.format(
                backup_prefix, valid_extensions))
    except tarfile.ReadError:
        msg = "DB file is not found inside tarfile and should be with valid {} extensions".format(valid_extensions)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except tarfile.CompressionError:
        msg = "Only gzip compression is supported"
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except (NameError, OSError, RuntimeError) as err_msg:
        msg = str(err_msg)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    except ValueError as err_msg:
        msg = str(err_msg)
        raise web.HTTPNotImplemented(reason=msg, body=json.dumps({"message": msg}))
    except Exception as exc:
        msg = str(exc)
        _logger.error("Failed to upload Backup. {}".format(msg))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        msg = "{} backup uploaded successfully.".format(file_name)
        return web.json_response({"message": msg})
    finally:
        # Remove temporary directory
        cmd = "rm -rf {}".format(temp_path)
        os.system(cmd)
