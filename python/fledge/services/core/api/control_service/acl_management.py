# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
import logging
from aiohttp import web


from fledge.common import logger
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.services.core import connect
from fledge.services.core.api.control_service.exceptions import *


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2021 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_logger = logger.setup(__name__, level=logging.INFO)


async def get_all_acls(request: web.Request) -> web.Response:
    """ Get list of all access control lists in the system

    :Example:
        curl -sX GET http://localhost:8081/fledge/ACL
    """
    storage = connect.get_storage_async()
    payload = PayloadBuilder().SELECT("name", "service", "url").payload()
    result = await storage.query_tbl_with_payload('control_acl', payload)
    all_acls = [key for key in result['rows']]
    # TODO: Add users list in response where they are used
    return web.json_response({"acls": all_acls})


async def get_acl(request: web.Request) -> web.Response:
    """ Get the details of access control list by name

    :Example:
        curl -sX GET http://localhost:8081/fledge/ACL/testACL
    """
    try:
        name = request.match_info.get('acl_name', None)
        storage = connect.get_storage_async()
        payload = PayloadBuilder().SELECT("name", "service", "url").WHERE(['name', '=', name]).payload()
        result = await storage.query_tbl_with_payload('control_acl', payload)
        if 'rows' in result:
            if result['rows']:
                acl_info = result['rows'][0]
            else:
                raise NameNotFoundError('No such {} ACL found'.format(name))
        else:
            raise StorageServerError(result)
    except StorageServerError as err:
        msg = "Storage error: {}".format(str(err))
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    except NameNotFoundError as err:
        msg = str(err)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))
    except Exception as ex:
        msg = str(ex)
        raise web.HTTPInternalServerError(reason=msg, body=json.dumps({"message": msg}))
    else:
        return web.json_response(acl_info)
