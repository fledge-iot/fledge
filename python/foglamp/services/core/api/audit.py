# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from datetime import datetime
import json
from enum import IntEnum
from collections import OrderedDict
from aiohttp import web

from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.services.core import connect
from foglamp.common.audit_logger import AuditLogger
from foglamp.common import logger

__author__ = "Amarendra K. Sinha, Ashish Jabble, Massimiliano Pinto"
__copyright__ = "Copyright (c) 2017-2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__DEFAULT_LIMIT = 20
__DEFAULT_OFFSET = 0

_help = """
    -------------------------------------------------------------------------------
    | GET POST        | /foglamp/audit                                            |
    | GET             | /foglamp/audit/logcode                                    |
    | GET             | /foglamp/audit/severity                                   |
    -------------------------------------------------------------------------------
"""

_LOG_LEVEL = 20
_logger = logger.setup(__name__, level=_LOG_LEVEL)


class Severity(IntEnum):
    """ Enumeration for log.severity """
    # TODO: FOGL-1100, no info for 3
    SUCCESS = 0
    FAILURE = 1
    WARNING = 2
    INFORMATION = 4

####################################
#  Audit Trail
####################################


async def create_audit_entry(request):
    """ Creates a new Audit entry

    Args:
        request: POST /foglamp/audit

        {
          "source"   : "LMTR", # 5 char max
          "severity" : "WARNING",
          "details"  : {
                        "message" : "Engine oil pressure low"
                      }
        }

    :Example:

        curl -X POST -d '{"source":"LMTR","severity":"WARNING","details":{"message":"Engine oil pressure low"}}
        http://localhost:8081/foglamp/audit

    Returns:
        json object representation of created audit entry

        {
          "timestamp" : "2017-06-21T09:39:51.8949395",
          "source"    : "LMTR",
          "severity"  : "WARNING",
          "details"   : {
                         "message" : "Engine oil pressure low"
                        }
        }
    """
    return_error = False
    err_msg = "Missing required parameter"

    payload = await request.json()

    severity = payload.get("severity")
    source = payload.get("source")
    details = payload.get("details")

    if severity is None or severity == "":
        err_msg += " severity"
        return_error = True
    if source is None or source == "":
        err_msg += " source"
        return_error = True
    if details is None:
        err_msg += " details"
        return_error = True

    if return_error:
        raise web.HTTPBadRequest(reason=err_msg)

    if not isinstance(details, dict):
        raise web.HTTPBadRequest(reason="Details should be a valid json object")

    try:
        audit = AuditLogger()
        await getattr(audit, str(severity).lower())(source, details)

        # Set timestamp for return message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        message = {'timestamp': str(timestamp),
                   'source': source,
                   'severity': severity,
                   'details': details
                   }
        return web.json_response(message)
    except AttributeError as e:
        # Return error for wrong severity method
        err_msg = "severity type {} is not supported".format(severity)
        _logger.error("Error in create_audit_entry(): %s | %s", err_msg, str(e))
        raise web.HTTPNotFound(reason=err_msg)
    except Exception as ex:
        raise web.HTTPInternalServerError(reason=str(ex))


async def get_audit_entries(request):
    """ Returns a list of audit trail entries sorted with most recent first and total count
        (including the criteria search if applied)

    :Example:

        curl -X GET http://localhost:8081/foglamp/audit

        curl -X GET http://localhost:8081/foglamp/audit?limit=5

        curl -X GET http://localhost:8081/foglamp/audit?limit=5&skip=3

        curl -X GET http://localhost:8081/foglamp/audit?skip=2

        curl -X GET http://localhost:8081/foglamp/audit?source=PURGE

        curl -X GET http://localhost:8081/foglamp/audit?severity=FAILURE

        curl -X GET http://localhost:8081/foglamp/audit?source=LOGGN&severity=INFORMATION&limit=10
    """

    limit = __DEFAULT_LIMIT
    if 'limit' in request.query and request.query['limit'] != '':
        try:
            limit = int(request.query['limit'])
            if limit < 0:
                raise ValueError
        except ValueError:
            raise web.HTTPBadRequest(reason="Limit must be a positive integer")

    offset = __DEFAULT_OFFSET
    if 'skip' in request.query and request.query['skip'] != '':
        try:
            offset = int(request.query['skip'])
            if offset < 0:
                raise ValueError
        except ValueError:
            raise web.HTTPBadRequest(reason="Skip/Offset must be a positive integer")

    source = None
    if 'source' in request.query and request.query['source'] != '':
        try:
            source = request.query.get('source')
            # SELECT * FROM log_codes
            storage_client = connect.get_storage()
            result = storage_client.query_tbl("log_codes")
            log_codes = [key['code'] for key in result['rows']]
            if source not in log_codes:
                raise ValueError
        except ValueError:
            raise web.HTTPBadRequest(reason="{} is not a valid source".format(source))

    severity = None
    if 'severity' in request.query and request.query['severity'] != '':
        try:
            severity = Severity[request.query['severity'].upper()].value
        except KeyError as ex:
            raise web.HTTPBadRequest(reason="{} is not a valid severity".format(ex))

    try:
        # HACK: This way when we can more future we do not get an exponential
        # explosion of if statements
        payload = PayloadBuilder().WHERE(['1', '=', 1])
        if source is not None:
            payload.AND_WHERE(['code', '=', source])

        if severity is not None:
            payload.AND_WHERE(['level', '=', severity])

        _and_where_payload = payload.chain_payload()
        # SELECT *, count(*) OVER() FROM log - No support yet from storage layer
        # TODO: FOGL-740, FOGL-663 once ^^ resolved we should replace below storage call for getting total rows
        # TODO: FOGL-643 - Aggregate with alias support needed to use payload builder
        aggregate = {"operation": "count", "column": "*", "alias": "count"}
        d = OrderedDict()
        d['aggregate'] = aggregate
        d.update(_and_where_payload)
        total_count_payload = json.dumps(d)

        # SELECT count (*) FROM log <_and_where_payload>
        storage_client = connect.get_storage()
        result = storage_client.query_tbl_with_payload('log', total_count_payload)
        total_count = result['rows'][0]['count']

        payload.ORDER_BY(['ts', 'desc'])
        payload.LIMIT(limit)

        if offset > 0:
            payload.OFFSET(offset)

        # SELECT * FROM log <payload.payload()>
        results = storage_client.query_tbl_with_payload('log', payload.payload())
        res = []
        for row in results['rows']:
            r = dict()
            r["details"] = row["log"]
            severity_level = int(row["level"])
            r["severity"] = Severity(severity_level).name if severity_level in (0, 1, 2, 4) else "UNKNOWN"
            r["source"] = row["code"]
            r["timestamp"] = row["ts"]

            res.append(r)

    except Exception as ex:
        raise web.HTTPException(reason=str(ex))

    return web.json_response({'audit': res, 'totalCount': total_count})


async def get_audit_log_codes(request):
    """
    Args:
        request:

    Returns:
           an array of log codes with description

    :Example:

        curl -X GET http://localhost:8081/foglamp/audit/logcode
    """
    storage_client = connect.get_storage()
    result = storage_client.query_tbl('log_codes')

    return web.json_response({'logCode': result['rows']})


async def get_audit_log_severity(request):
    """
    Args:
        request:

    Returns:
            an array of audit severity enumeration key index values

    :Example:

        curl -X GET http://localhost:8081/foglamp/audit/severity
    """
    results = []
    for _severity in Severity:
        data = {'index': _severity.value, 'name': _severity.name}
        results.append(data)

    return web.json_response({"logSeverity": results})
