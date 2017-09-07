# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Service Registry Rest API support"""

import time
from aiohttp import web
from foglamp.core.service_registry.instance import Service

__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__start_time = time.time()

_help = """
    -----------------------------------------------------------------------------------
    | GET             | /foglamp/service/ping                                          |
    | GET             | /foglamp/service?name=&type= (name | type optional query param)|
    | GET, POST       | /foglamp/service                                               |
    | DELETE          | /foglamp/service/{service_id}                                  |
    -----------------------------------------------------------------------------------
"""

async def ping(request):
    since_started = time.time() - __start_time
    return web.json_response({'uptime': since_started})

async def register(request):
    """
    Register a service

    :Example: curl -d '{"type": "Storage", "name": "Storage Services", "address": "127.0.0.1", "port": 8090,
            "protocol": "https"}' -X POST http://localhost:8082/foglamp/service
    """

    try:
        data = await request.json()

        service_name = data.get('name', None)
        service_type = data.get('type', None)
        service_address = data.get('address', None)
        service_port = data.get('port', None)
        service_protocol = data.get('protocol', 'http')

        if not (service_name or service_type or service_address or service_port):
            return web.json_response({'error': 'One or more values for type/name/address/port missing'})
        if not isinstance(service_port, int):
            return web.json_response({'error': 'Service port can be a positive integer only'})

        try:
            registered_service_id = Service.Instances.register(service_name,service_type,
                                                               service_address, service_port, service_protocol)
        # TODO map the raised exception message
        except Service.AlreadyExistsWithTheSameName:
            return web.json_response({'error': 'Service with the same name already exists'})

        except Service.AlreadyExistsWithTheSameAddressAndPort:
            return web.json_response({'error': 'Service with the same address and port already exists'})

        if not registered_service_id:
            return web.json_response({'error': 'Service {} could not be registered'.format(service_name)})

        _response = {
            'id': registered_service_id,
            'message': "Service registered successfully"
        }

        return web.json_response(_response)

    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))

async def unregister(request):
    """
    Unregister a service

    :Example: curl -X DELETE  http://localhost:8082/foglamp/service/dc9bfc01-066a-4cc0-b068-9c35486db87f
    """

    try:
        service_id = request.match_info.get('service_id', None)

        if not service_id:
            return web.json_response({'error': 'Service id is required'})

        try:
            Service.Instances.get(idx=service_id)
        except Service.DoesNotExist:
            return web.json_response({'error': 'Service with {} does not exist'.format(service_id)})

        Service.Instances.unregister(service_id)

        _resp = {'id': str(service_id), 'message': 'Service unregistered'}

        return web.json_response(_resp)
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))


async def get_service(request):
    """
    Returns a list of all services or of the selected service

    :Example: curl -X GET  http://localhost:8082/foglamp/service
    :Example: curl -X GET  http://localhost:8082/foglamp/service?name=X&type=Storage
    """

    try:

        service_name = request.query['name'] if 'name' in request.query else None
        service_type = request.query['type'] if 'type' in request.query else None

        try:
            if not service_name and not service_type:
                services_list = Service.Instances.all()
            elif service_name and not service_type:
                services_list = Service.Instances.get(name=service_name)
            elif not service_name and service_type:
                services_list = Service.Instances.get(s_type=service_type)
            else:
                services_list = Service.Instances.filter_by_name_and_type(
                        name=service_name, s_type=service_type
                    )
        except Service.DoesNotExist:
            return web.json_response({"services": []})

        services = []
        for service in services_list:
            services.append({
                "id": service._id,
                "name": service._name,
                "type": service._type,
                "address": service._address,
                "port": service._port,
                "protocol": service._protocol
            })
        return web.json_response({"services": services})
    except Exception as ex:
        raise web.HTTPInternalServerError(reason='FogLAMP has encountered an internal error', text=str(ex))

async def shutdown(request):
    pass

async def register_interest(request):
    pass

async def unregister_interest(request):
    pass

async def notify_change(request):
    pass
