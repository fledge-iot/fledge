# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test fledge.services.core server """

import asyncio
import json
from unittest import mock
from unittest.mock import MagicMock, patch
from aiohttp import web
from aiohttp.test_utils import make_mocked_request
from aiohttp.streams import StreamReader
from multidict import CIMultiDict
import pytest

from fledge.services.common.microservice_management import routes as management_routes
from fledge.services.core import server
from fledge.services.core.server import Server
from fledge.common.web import middleware
from fledge.services.core.interest_registry.interest_registry import InterestRegistry
from fledge.services.core.interest_registry.interest_record import InterestRecord
from fledge.services.core.interest_registry import exceptions as interest_registry_exceptions
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.common.service_record import ServiceRecord
from fledge.services.core.service_registry import exceptions as service_registry_exceptions
from fledge.services.core.api import configuration as conf_api
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.audit_logger import AuditLogger


__author__ = "Vaibhav Singhal, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def mock_request(data, loop):
    payload = StreamReader("http", loop=loop)
    payload.feed_data(data.encode())
    payload.feed_eof()

    protocol = mock.Mock()
    app = mock.Mock()
    headers = CIMultiDict([('CONTENT-TYPE', 'application/json')])
    req = make_mocked_request('POST', '/sensor-reading', headers=headers,
                              protocol=protocol, payload=payload, app=app, loop=loop)
    return req


@pytest.allure.feature("unit")
@pytest.allure.story("services", "core", "server")
class TestServer:

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(middlewares=[middleware.error_middleware])
        management_routes.setup(app, Server, True)
        return loop.run_until_complete(test_client(app))

    ############################
    # start stop
    ############################

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test_get_certificates(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__rest_api_config(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test_service_config(self):
        pass

    async def test__installation_config(self):
        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        Server._configuration_manager = ConfigurationManager(storage_client_mock)

        with patch.object(Server._configuration_manager, 'create_category',
                          return_value=async_mock([])) as patch_create_cat:
            with patch.object(Server._configuration_manager, 'get_category_all_items',
                              return_value=async_mock([])) as patch_get_all_cat:
                await Server.installation_config()
            patch_get_all_cat.assert_called_once_with('Installation')
        patch_create_cat.assert_called_once_with('Installation', Server._INSTALLATION_DEFAULT_CONFIG, 'Installation',
                                                 True, display_name='Installation')

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__make_app(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__make_core_app(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__start_service_monitor(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test_stop_service_monitor(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test___start_scheduler(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__start_storage(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__start_storage(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__get_storage_client(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__start_app(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test_pid_filename(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__pidfile_exists(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__remove_pid(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__write_pid(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__start_core(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__register_core(self):
        pass

    @pytest.mark.asyncio
    async def test_start(self):
        with patch.object(Server, "_start_core", return_value=None) as patched_start_core:
            Server.start()
        args, kwargs = patched_start_core.call_args
        assert 1 == patched_start_core.call_count
        assert isinstance(kwargs['loop'], asyncio.unix_events._UnixSelectorEventLoop)

    @pytest.mark.asyncio
    async def test__stop(self, mocker):
        mocked__stop_scheduler = mocker.patch.object(Server, "_stop_scheduler")
        mocked_stop_microservices = mocker.patch.object(Server, "stop_microservices")
        mocked_stop_service_monitor = mocker.patch.object(Server, "stop_service_monitor")
        mocked_stop_rest_server = mocker.patch.object(Server, "stop_rest_server")
        mocked_stop_storage = mocker.patch.object(Server, "stop_storage")
        mocked__remove_pid = mocker.patch.object(Server, "_remove_pid")

        async def return_async_value(val):
            return val

        mocked__stop_scheduler.return_value = return_async_value('stopping scheduler..')
        mocked_stop_microservices.return_value = return_async_value('stopping msvc..')
        mocked_stop_service_monitor.return_value = return_async_value('stopping svc monitor..')
        mocked_stop_rest_server.return_value = return_async_value('stopping REST server..')
        mocked_stop_storage.return_value = return_async_value('stopping storage..')

        mocked__remove_pid.return_value = 'removing PID..'

        with patch.object(AuditLogger, '__init__', return_value=None):
            with patch.object(AuditLogger, 'information', return_value=return_async_value(None)) as audit_info_patch:
                await Server._stop()
            # Must write the audit log entry before we stop the storage service
            args, kwargs = audit_info_patch.call_args
            assert 'FSTOP' == args[0]
            assert None is args[1]

        assert 1 == mocked__stop_scheduler.call_count
        assert 1 == mocked_stop_microservices.call_count
        assert 1 == mocked_stop_service_monitor.call_count
        assert 1 == mocked_stop_rest_server.call_count
        assert 1 == mocked_stop_storage.call_count
        assert 1 == mocked__remove_pid.call_count

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test_stop_rest_server(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test_stop_storage(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test_stop_microservices(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__request_microservice_shutdown(self):
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="To be implemented")
    async def test__stop_scheduler(self):
        pass

    ############################
    # Configuration Management
    ############################

    """ Tests the calls to configuration manager via core management api
    
    No negative tests added since these are already covered in fledge/services/core/api/test_configuration.py
    """
    async def test_get_configuration_categories(self, client):
        async def async_mock():
            return web.json_response({'categories': "test"})

        result = {'categories': "test"}
        with patch.object(conf_api, 'get_categories', return_value=async_mock()) as patch_get_all_categories:
            resp = await client.get('/fledge/service/category')
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert result == json_response
        assert 1 == patch_get_all_categories.call_count

    async def test_get_configuration_category(self, client):
        async def async_mock():
            return web.json_response("test")

        result = "test"
        with patch.object(conf_api, 'get_category', return_value=async_mock()) as patch_category:
            resp = await client.get('/fledge/service/category/{}'.format("test_category"))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert result == json_response
        assert 1 == patch_category.call_count

    async def test_create_configuration_category(self, client):
        async def async_mock():
            return web.json_response({"key": "test_name",
                                      "description": "test_category_desc",
                                      "value": "test_category_info"})

        result = {"key": "test_name", "description": "test_category_desc", "value": "test_category_info"}
        with patch.object(conf_api, 'create_category', return_value=async_mock()) as patch_create_category:
            resp = await client.post('/fledge/service/category')
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert result == json_response
        assert 1 == patch_create_category.call_count

    async def test_get_configuration_item(self, client):
        async def async_mock():
            return web.json_response("test")

        result = "test"
        with patch.object(conf_api, 'get_category_item', return_value=async_mock()) as patch_category_item:
            resp = await client.get('/fledge/service/category/{}/{}'.format("test_category", "test_item"))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert result == json_response
        assert 1 == patch_category_item.call_count

    async def test_update_configuration_item(self, client):
        async def async_mock():
            return web.json_response("test")

        result = "test"
        with patch.object(conf_api, 'set_configuration_item', return_value=async_mock()) as patch_update_category_item:
            resp = await client.put('/fledge/service/category/{}/{}'.format("test_category", "test_item"))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert result == json_response
        assert 1 == patch_update_category_item.call_count

    async def test_delete_configuration_item(self, client):
        async def async_mock():
            return web.json_response("ok")

        result = "ok"
        with patch.object(conf_api, 'delete_configuration_item_value', return_value=async_mock()) as patch_del_category_item:
            resp = await client.delete('/fledge/service/category/{}/{}/value'.format("test_category", "test_item"))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert result == json_response
        assert 1 == patch_del_category_item.call_count

    ############################
    # Register Interest
    ############################
    async def test_bad_uuid_get_interest(self, client):
        resp = await client.get('/fledge/interest?microserviceid=X')
        assert 400 == resp.status
        assert 'Invalid microservice id X' == resp.reason

    @pytest.mark.parametrize("params, expected_kwargs", [
        ("", {}),
        ("?category=Y", {'category_name': 'Y'}),
        ("?microserviceid=c6bbf3c8-f43c-4b0f-ac48-f597f510da0b", {'microservice_uuid': 'c6bbf3c8-f43c-4b0f-ac48-f597f510da0b'}),
        ("?category=Y&microserviceid=0c501cd3-c45a-439a-bec6-fc08d13f9699",  {'microservice_uuid': '0c501cd3-c45a-439a-bec6-fc08d13f9699', 'category_name': 'Y'})
    ])
    async def test_get_interest_with_filter(self, client, params, expected_kwargs):
        Server._storage_client = MagicMock(StorageClientAsync)
        Server._configuration_manager = ConfigurationManager(Server._storage_client)
        Server._interest_registry = InterestRegistry(Server._configuration_manager)
        with patch.object(Server._interest_registry, 'get', return_value=[]) as patch_get_interest_reg:
            resp = await client.get('/fledge/interest{}'.format(params))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert {'interests': []} == json_response
        args, kwargs = patch_get_interest_reg.call_args
        assert expected_kwargs == kwargs

    @pytest.mark.parametrize("params, expected_kwargs, message", [
        ("", {}, "No interest registered"),
        ("?category=Y", {'category_name': 'Y'}, "No interest registered for category Y"),
        ("?microserviceid=c6bbf3c8-f43c-4b0f-ac48-f597f510da0b",
         {'microservice_uuid': 'c6bbf3c8-f43c-4b0f-ac48-f597f510da0b'}, "No interest registered microservice id c6bbf3c8-f43c-4b0f-ac48-f597f510da0b"),
        ("?category=Y&microserviceid=0c501cd3-c45a-439a-bec6-fc08d13f9699",
         {'microservice_uuid': '0c501cd3-c45a-439a-bec6-fc08d13f9699', 'category_name': 'Y'}, "No interest registered for category Y and microservice id 0c501cd3-c45a-439a-bec6-fc08d13f9699")
    ])
    async def test_get_interest_exception(self, client, params, message, expected_kwargs):
        Server._storage_client = MagicMock(StorageClientAsync)
        Server._configuration_manager = ConfigurationManager(Server._storage_client)
        Server._interest_registry = InterestRegistry(Server._configuration_manager)
        with patch.object(Server._interest_registry, 'get', side_effect=interest_registry_exceptions.DoesNotExist) as patch_get_interest_reg:
            resp = await client.get('/fledge/interest{}'.format(params))
            assert 404 == resp.status
            assert message == resp.reason
        args, kwargs = patch_get_interest_reg.call_args
        assert expected_kwargs == kwargs

    async def test_get_interest(self, client):
        Server._storage_client = MagicMock(StorageClientAsync)
        Server._configuration_manager = ConfigurationManager(Server._storage_client)
        Server._interest_registry = InterestRegistry(Server._configuration_manager)

        data = []
        category_name = 'test_Cat'
        muuid = '0c501cd3-c45a-439a-bec6-fc08d13f9699'
        reg_id = 'c6bbf3c8-f43c-4b0f-ac48-f597f510da0b'
        record = InterestRecord(reg_id, muuid, category_name)
        data.append(record)

        with patch.object(Server._interest_registry, 'get', return_value=data) as patch_get_interest_reg:
            resp = await client.get('/fledge/interest')
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert {'interests': [{'category': category_name, 'microserviceId': muuid, 'registrationId': reg_id}]} == json_response
        args, kwargs = patch_get_interest_reg.call_args
        assert {} == kwargs

    async def test_bad_uuid_register_interest(self, client):
        request_data = {"category": "COAP", "service": "X"}
        resp = await client.post('/fledge/interest', data=json.dumps(request_data))
        assert 400 == resp.status
        assert 'Invalid microservice id X' == resp.reason

    async def test_bad_register_interest(self, client):
        Server._storage_client = MagicMock(StorageClientAsync)
        Server._configuration_manager = ConfigurationManager(Server._storage_client)
        Server._interest_registry = InterestRegistry(Server._configuration_manager)

        request_data = {"category": "COAP", "service": "c6bbf3c8-f43c-4b0f-ac48-f597f510da0b"}
        with patch.object(Server._interest_registry, 'register', return_value=None) as patch_reg_interest_reg:
            resp = await client.post('/fledge/interest', data=json.dumps(request_data))
            assert 400 == resp.status
            assert 'Interest by microservice_uuid {} for category_name {} could not be registered'.format(request_data['service'], request_data['category']) == resp.reason
        args, kwargs = patch_reg_interest_reg.call_args
        assert (request_data['service'], request_data['category']) == args

    async def test_register_interest_exceptions(self, client):
        Server._storage_client = MagicMock(StorageClientAsync)
        Server._configuration_manager = ConfigurationManager(Server._storage_client)
        Server._interest_registry = InterestRegistry(Server._configuration_manager)

        request_data = {"category": "COAP", "service": "c6bbf3c8-f43c-4b0f-ac48-f597f510da0b"}
        with patch.object(Server._interest_registry, 'register', side_effect=interest_registry_exceptions.ErrorInterestRegistrationAlreadyExists) as patch_reg_interest_reg:
            resp = await client.post('/fledge/interest', data=json.dumps(request_data))
            assert 400 == resp.status
            assert 'An InterestRecord already exists by microservice_uuid {} for category_name {}'.format(request_data['service'], request_data['category']) == resp.reason
        args, kwargs = patch_reg_interest_reg.call_args
        assert (request_data['service'], request_data['category']) == args

    async def test_register_interest(self, client):
        Server._storage_client = MagicMock(StorageClientAsync)
        Server._configuration_manager = ConfigurationManager(Server._storage_client)
        Server._interest_registry = InterestRegistry(Server._configuration_manager)

        request_data = {"category": "COAP", "service": "c6bbf3c8-f43c-4b0f-ac48-f597f510da0b"}
        reg_id = 'a404852d-d91c-47bd-8860-d4ff81b6e8cb'
        with patch.object(Server._interest_registry, 'register', return_value=reg_id) as patch_reg_interest_reg:
            resp = await client.post('/fledge/interest', data=json.dumps(request_data))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert {'id': reg_id, 'message': 'Interest registered successfully'} == json_response
        args, kwargs = patch_reg_interest_reg.call_args
        assert (request_data['service'], request_data['category']) == args

    async def test_bad_uuid_unregister_interest(self, client):
        resp = await client.delete('/fledge/interest/blah')
        assert 400 == resp.status
        assert 'Invalid registration id blah' == resp.reason

    async def test_unregister_interest_exception(self, client):
        Server._storage_client = MagicMock(StorageClientAsync)
        Server._configuration_manager = ConfigurationManager(Server._storage_client)
        Server._interest_registry = InterestRegistry(Server._configuration_manager)

        reg_id = 'c6bbf3c8-f43c-4b0f-ac48-f597f510da0b'
        with patch.object(Server._interest_registry, 'get', side_effect=interest_registry_exceptions.DoesNotExist) as patch_get_interest_reg:
            resp = await client.delete('/fledge/interest/{}'.format(reg_id))
            assert 404 == resp.status
            assert 'InterestRecord with registration_id {} does not exist'.format(reg_id) == resp.reason
        args, kwargs = patch_get_interest_reg.call_args
        assert {'registration_id': reg_id} == kwargs

    async def test_unregister_interest(self, client):
        Server._storage_client = MagicMock(StorageClientAsync)
        Server._configuration_manager = ConfigurationManager(Server._storage_client)
        Server._interest_registry = InterestRegistry(Server._configuration_manager)

        data = []
        category_name = 'test_Cat'
        muuid = '0c501cd3-c45a-439a-bec6-fc08d13f9699'
        reg_id = 'c6bbf3c8-f43c-4b0f-ac48-f597f510da0b'
        record = InterestRecord(reg_id, muuid, category_name)
        data.append(record)

        with patch.object(Server._interest_registry, 'get', return_value=data) as patch_get_interest_reg:
            with patch.object(Server._interest_registry, 'unregister', return_value=[]) as patch_unregister_interest:
                resp = await client.delete('/fledge/interest/{}'.format(reg_id))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert {'id': reg_id, 'message': 'Interest unregistered'} == json_response
            args, kwargs = patch_unregister_interest.call_args
            assert (reg_id,) == args
        args1, kwargs1 = patch_get_interest_reg.call_args
        assert {'registration_id': reg_id} == kwargs1

    ############################
    # Register Service
    ############################
    @pytest.mark.parametrize("params, obj, expected_kwargs", [
        ("", "all", {}),
        ("?name=Y", "get", {'name': 'Y'}),
        ("?type=Storage", "get", {'s_type': 'Storage'}),
        ("?name=Y&type=Storage", "filter_by_name_and_type", {'name': 'Y', 's_type': 'Storage'})
    ])
    async def test_get_service(self, client, params, obj, expected_kwargs):
        with patch.object(ServiceRegistry, obj, return_value=[]) as patch_get_service_reg:
            resp = await client.get('/fledge/service{}'.format(params))
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert {'services': []} == json_response
        args, kwargs = patch_get_service_reg.call_args
        assert expected_kwargs == kwargs

    @pytest.mark.parametrize("params, obj, expected_kwargs, message", [
        ("", "all", {}, "No service found"),
        ("?name=Y", "get", {'name': 'Y'}, "Service with name Y does not exist"),
        ("?type=Storage", "get", {'s_type': 'Storage'}, "Service with type Storage does not exist"),
        ("?name=Y&type=Storage", "filter_by_name_and_type", {'name': 'Y', 's_type': 'Storage'}, "Service with name Y and type Storage does not exist")
    ])
    async def test_get_service_exception(self, client, params, obj, expected_kwargs, message):
        with patch.object(ServiceRegistry, obj, side_effect=service_registry_exceptions.DoesNotExist) as patch_service_reg:
            resp = await client.get('/fledge/service{}'.format(params))
            assert 404 == resp.status
            assert message == resp.reason
        args, kwargs = patch_service_reg.call_args
        assert expected_kwargs == kwargs

    async def test_get_services(self, client):
        sid = "c6bbf3c8-f43c-4b0f-ac48-f597f510da0b"
        sname = "name"
        stype = "Southbound"
        sprotocol = "http"
        saddress = "localhost"
        sport = 1234
        smgtport = 4321
        data = []
        record = ServiceRecord(sid, sname, stype, sprotocol, saddress, sport, smgtport)
        data.append(record)

        with patch.object(ServiceRegistry, 'all', return_value=data) as patch_get_all_service_reg:
            resp = await client.get('/fledge/service')
            assert 200 == resp.status
            r = await resp.text()
            json_response = json.loads(r)
            assert {'services': [{'id': sid, 'management_port': smgtport, 'address': saddress, 'name': sname, 'type': stype, 'protocol': sprotocol, 'status': 'running', 'service_port': sport}]} == json_response
        args, kwargs = patch_get_all_service_reg.call_args
        assert {} == kwargs

    @pytest.mark.parametrize("request_data, message", [
        ({"type": "Storage", "name": "Storage Services", "address": "127.0.0.1", "service_port": "8090", "management_port": 1090}, "Service's service port can be a positive integer only"),
        ({"type": "Storage", "name": "Storage Services", "address": "127.0.0.1", "service_port": 8090, "management_port": "1090"}, "Service management port can be a positive integer only"),
        ({"type": "Storage", "name": "Storage Services", "address": "127.0.0.1", "service_port": "8090", "management_port": "1090"}, "Service's service port can be a positive integer only")
    ])
    async def test_bad_register_service(self, client, request_data, message):
        resp = await client.post('/fledge/service', data=json.dumps(request_data))
        assert 400 == resp.status
        assert message == resp.reason

    @pytest.mark.parametrize("exception_name, message", [
        (service_registry_exceptions.AlreadyExistsWithTheSameName, "A Service with the same name already exists"),
        (service_registry_exceptions.AlreadyExistsWithTheSameAddressAndPort, "A Service is already registered on the same address: 127.0.0.1 and service port: 8090"),
        (service_registry_exceptions.AlreadyExistsWithTheSameAddressAndManagementPort, "A Service is already registered on the same address: 127.0.0.1 and management port: 1090")
    ])
    async def test_register_service_exceptions(self, client, exception_name, message):
        request_data = {"type": "Storage", "name": "Storage Services", "address": "127.0.0.1", "service_port": 8090, "management_port": 1090}
        with patch.object(ServiceRegistry, 'register', side_effect=exception_name):
            resp = await client.post('/fledge/service', data=json.dumps(request_data))
            assert 400 == resp.status
            assert message == resp.reason

    async def test_service_not_registered(self, client):
        request_data = {"type": "Storage", "name": "Storage Services", "address": "127.0.0.1", "service_port": 8090, "management_port": 1090}
        with patch.object(ServiceRegistry, 'register', return_value=None) as patch_register:
            resp = await client.post('/fledge/service', data=json.dumps(request_data))
            assert 400 == resp.status
            assert 'Service {} could not be registered'.format(request_data['name']) == resp.reason
        args, kwargs = patch_register.call_args
        assert (request_data['name'], request_data['type'], request_data['address'],  request_data['service_port'], request_data['management_port'], 'http', None) == args

    async def test_register_service(self, client):
        async def async_mock(return_value):
            return return_value

        Server._storage_client = MagicMock(StorageClientAsync)
        Server._storage_client_async = MagicMock(StorageClientAsync)
        request_data = {"type": "Storage", "name": "Storage Services", "address": "127.0.0.1", "service_port": 8090, "management_port": 1090}
        with patch.object(ServiceRegistry, 'register', return_value='1') as patch_register:
            with patch.object(AuditLogger, '__init__', return_value=None):
                with patch.object(AuditLogger, 'information', return_value=async_mock(None)) as audit_info_patch:
                    resp = await client.post('/fledge/service', data=json.dumps(request_data))
                    assert 200 == resp.status
                    r = await resp.text()
                    json_response = json.loads(r)
                    assert {'message': 'Service registered successfully', 'id': '1', 'bearer_token': ''} == json_response
                args, kwargs = audit_info_patch.call_args
                assert 'SRVRG' == args[0]
                assert {'name': request_data['name']} == args[1]
        args, kwargs = patch_register.call_args
        assert (request_data['name'], request_data['type'], request_data['address'], request_data['service_port'], request_data['management_port'], 'http', None) == args

    async def test_service_not_found_when_unregister(self, client):
        with patch.object(ServiceRegistry, 'get', side_effect=service_registry_exceptions.DoesNotExist) as patch_unregister:
            resp = await client.delete('/fledge/service/blah')
            assert 404 == resp.status
            assert 'Service with blah does not exist' == resp.reason
        args, kwargs = patch_unregister.call_args
        assert {'idx': 'blah'} == kwargs

    async def test_unregister_service(self, client):
        async def async_mock():
            return ""

        service_id = "c6bbf3c8-f43c-4b0f-ac48-f597f510da0b"
        sname = "name"
        stype = "Southbound"
        sprotocol = "http"
        saddress = "localhost"
        sport = 1234
        smgtport = 4321
        data = []
        record = ServiceRecord(service_id, sname, stype, sprotocol, saddress, sport, smgtport)
        data.append(record)
        Server._storage_client = MagicMock(StorageClientAsync)
        Server._storage_client_async = MagicMock(StorageClientAsync)
        with patch.object(ServiceRegistry, 'get', return_value=data) as patch_get_unregister:
            with patch.object(ServiceRegistry, 'unregister') as patch_unregister:
                with patch.object(AuditLogger, '__init__', return_value=None):
                    with patch.object(AuditLogger, 'information', return_value=async_mock()) as audit_info_patch:
                        resp = await client.delete('/fledge/service/{}'.format(service_id))
                        assert 200 == resp.status
                        r = await resp.text()
                        json_response = json.loads(r)
                        assert {'id': service_id, 'message': 'Service unregistered'} == json_response
                    args, kwargs = audit_info_patch.call_args
                    assert 'SRVUN' == args[0]
                    assert {'name': sname} == args[1]
            args1, kwargs1 = patch_unregister.call_args
            assert (service_id,) == args1
        args2, kwargs2 = patch_get_unregister.call_args
        assert {'idx': service_id} == kwargs2

    ############################
    # Common
    ############################
    async def test_ping(self, client):
        resp = await client.get('/fledge/service/ping')
        assert 200 == resp.status
        r = await resp.text()
        json_response = json.loads(r)
        assert 'uptime' in json_response
        assert 0.0 < json_response["uptime"]

    @pytest.mark.asyncio
    async def test_shutdown(self, mocker):
        async def return_async_value(val):
            return val

        mocked__stop = mocker.patch.object(Server, "_stop")
        mocked__stop.return_value = return_async_value('stopping...')
        mocked_log_info = mocker.patch.object(server._logger, "info")

        request = mock_request(data="", loop=asyncio.get_event_loop())
        resp = await Server.shutdown(request)

        assert 1 == mocked__stop.call_count
        assert 200 == resp.status

        json_response = json.loads(resp.body.decode())

        assert 1 == mocked_log_info.call_count
        args, kwargs = mocked_log_info.call_args
        assert 'Stopping the Fledge Core event loop. Good Bye!' == args[0]
        assert 'message' in json_response
        assert 'Fledge stopped successfully. Wait for few seconds for process cleanup.' == json_response["message"]

    async def test_change(self):
        pass
