# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from aiohttp import web

from foglamp.core.api import audit_trail_db_services

__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    -------------------------------------------------------------------------------
    | GET             | /foglamp/audit                                            |
    | GET             | /foglamp/audit/logcode                                    |
    | GET             | /foglamp/audit/severity                                   |
    -------------------------------------------------------------------------------
"""

####################################
#  Audit Trail
####################################

async def get_audit_entries(request):
    """
    Returns a list of audit trail entries sorted with most recent first

    :Example:

        curl -X GET http://localhost:8082/foglamp/audit

        curl -X GET http://localhost:8082/foglamp/audit?limit=5

        curl -X GET http://localhost:8082/foglamp/audit?limit=5&skip=3

        curl -X GET http://localhost:8082/foglamp/audit?source=PURGE

        curl -X GET http://localhost:8082/foglamp/audit?severity=ERROR

        curl -X GET http://localhost:8082/foglamp/audit?source=LOGGN&severity=INFORMATION&limit=10
    """
    try:
        limit = request.query.get('limit') if 'limit' in request.query else 0
        offset = 0
        if limit:
            offset = request.query.get('skip') if 'skip' in request.query else 0
        source = request.query.get('source') if 'source' in request.query else None
        severity = request.query.get('severity') if 'severity' in request.query else None
        audit_entries = await audit_trail_db_services.read_audit_entries(limit=int(limit), offset=int(offset),
                                                                         source=source, severity=severity)

        return web.json_response({'audit': audit_entries})

    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def get_audit_log_codes(request):
    """
    Args:
        request:

    Returns:
           an array of log codes with description

    :Example:

        curl -X GET http://localhost:8082/foglamp/audit/logcode
    """

    log_codes = await audit_trail_db_services.read_log_codes()

    return web.json_response({'log_code': log_codes})


async def get_audit_log_severity(request):
    """
    Args:
        request:

    Returns:
            an array of audit severity enumeration key index values

    :Example:

        curl -X GET http://localhost:8082/foglamp/audit/severity
    """
    results = []
    for _severity in audit_trail_db_services.Severity:
        data = {'index': _severity.value, 'name': _severity.name}
        results.append(data)

    return web.json_response({"log_severity": results})
