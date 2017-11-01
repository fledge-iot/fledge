# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Service Registry Rest API support"""

import time
from aiohttp import web
from foglamp.microservice_management.service_registry.instance import Service

__author__ = "Amarendra Kumar Sinha, Praveen Garg"
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
    """ health check

    """
    since_started = time.time() - __start_time
    return web.json_response({'uptime': since_started})


async def register(request):
    """ Register a service

    :Example: curl -d '{"type": "Storage", "name": "Storage Services", "address": "127.0.0.1", "service_port": 8090,
            "management_port": 1090, "protocol": "https"}' -X POST http://localhost:8082/foglamp/service
    service_port is optional
    """

    try:
        data = await request.json()

        service_name = data.get('name', None)
        service_type = data.get('type', None)
        service_address = data.get('address', None)
        service_port = data.get('service_port', 0)
        service_management_port = data.get('management_port', None)
        service_protocol = data.get('protocol', 'http')

        # TODO: make service port optional? or it can point to mgt port if not provided?
        if not (service_name.strip() or service_type.strip() or service_address.strip()
                or service_port.strip() or not service_port.isdigit()
                or service_management_port.strip() or not service_management_port.isdigit()):
            raise web.HTTPBadRequest(reason='One or more values for type/name/address/port/management port missing')

        if not isinstance(service_port, int):
            raise web.HTTPBadRequest(reason="Service's service port can be a positive integer only")

        if not isinstance(service_management_port, int):
            raise web.HTTPBadRequest(reason='Service management port can be a positive integer only')

        try:
            registered_service_id = Service.Instances.register(service_name, service_type, service_address,
                                                               service_port, service_management_port, service_protocol)
        except Service.AlreadyExistsWithTheSameName:
            raise web.HTTPBadRequest(reason='A Service with the same name already exists')
        except Service.AlreadyExistsWithTheSameAddressAndPort:
            raise web.HTTPBadRequest(reason='A Service is already registered on the same address: {} and '
                                            'service port: {}'.format(service_address, service_port))
        except Service.AlreadyExistsWithTheSameAddressAndManagementPort:
            raise web.HTTPBadRequest(reason='A Service is already registered on the same address: {} and '
                                            'management port: {}'.format(service_address, service_management_port))

        if not registered_service_id:
            raise web.HTTPBadRequest(reason='Service {} could not be registered'.format(service_name))

        _response = {
            'id': registered_service_id,
            'message': "Service registered successfully"
        }

        return web.json_response(_response)

    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def unregister(request):
    """ Deregister a service

    :Example: curl -X DELETE  http://localhost:8082/foglamp/service/dc9bfc01-066a-4cc0-b068-9c35486db87f
    """

    try:
        service_id = request.match_info.get('service_id', None)

        if not service_id:
            raise web.HTTPBadRequest(reason='Service id is required')

        try:
            Service.Instances.get(idx=service_id)
        except Service.DoesNotExist:
            raise web.HTTPBadRequest(reason='Service with {} does not exist'.format(service_id))

        Service.Instances.unregister(service_id)

        _resp = {'id': str(service_id), 'message': 'Service unregistered'}

        return web.json_response(_resp)
    except ValueError as ex:
        raise web.HTTPNotFound(reason=str(ex))


async def get_service(request):
    """ Returns a list of all services or of the selected service

    :Example: curl -X GET  http://localhost:8082/foglamp/service
    :Example: curl -X GET  http://localhost:8082/foglamp/service?name=X&type=Storage
    """
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
    except Service.DoesNotExist as ex:
        raise web.HTTPBadRequest(reason="Invalid service name and/or type provided" + str(ex))

    services = []
    for service in services_list:
        svc = dict()
        svc["id"] = service._id
        svc["name"] = service._name
        svc["type"] = service._type
        svc["address"] = service._address
        svc["management_port"] = service._management_port
        svc["protocol"] = service._protocol
        if service._port:
            svc["service_port"] = service._port
        services.append(svc)

    return web.json_response({"services": services})


async def shutdown(request):
    pass


async def register_interest(request):
    pass


async def unregister_interest(request):
    pass


async def notify_change(request):
    pass
