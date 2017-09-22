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
    pass

async def create_backup(request):
    """
    Creates a backup

    :Example: curl -X POST http://localhost:8082/foglamp/backup
    """
    pass

async def get_backup_details(request):
    """
    Returns the details of a backup

    :Example: curl -X GET  http://localhost:8082/foglamp/backup/1
    """
    pass

async def delete_backup(request):
    """
    Delete a backup

    :Example: curl -X DELETE  http://localhost:8082/foglamp/backup/1
    """
    pass

async def restore_backup(request):
    """
    Restore from a backup

    :Example: curl -X PUT  http://localhost:8082/foglamp/backup/1/restore
    """
    pass
