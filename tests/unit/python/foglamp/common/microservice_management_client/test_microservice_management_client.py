# -*- coding: utf-8 -*-

import pytest

from unittest.mock import MagicMock
from unittest.mock import patch

from http.client import HTTPConnection, HTTPResponse
import json
from foglamp.common import logger
from foglamp.common.microservice_management_client import exceptions as client_exceptions
from foglamp.common.microservice_management_client.microservice_management_client import MicroserviceManagementClient

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "microservice-management-client")
class TestMicroserviceManagementClient:
    def test_constructor(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        assert hasattr(ms_mgt_client, '_management_client_conn')

    def test_register_service_good_id(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps({'id': 'bla'})
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.register_service({'keys': 'vals'})
        request_patch.assert_called_once_with(
            body='{"keys": "vals"}', method='POST', url='/foglamp/service')
        assert ret_value == {'id': 'bla'}

    def test_register_service_no_id(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps({'notid': 'bla'})
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(KeyError) as excinfo:
                    ms_mgt_client.register_service({})

    @pytest.mark.parametrize("status_code", [450, 550])
    def test_register_service_status_client_err(self, status_code):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        response_mock.status = status_code
        response_mock.reason = 'this is the reason'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(client_exceptions.MicroserviceManagementClientError) as excinfo:
                    ms_mgt_client.register_service({})

    def test_unregister_service_good_id(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps({'id': 'bla'})
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.unregister_service('someid')
        request_patch.assert_called_once_with(
            method='DELETE', url='/foglamp/service/someid')

    def test_unregister_service_no_id(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps({'notid': 'bla'})
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(KeyError) as excinfo:
                    ret_value = ms_mgt_client.unregister_service('someid')

    @pytest.mark.parametrize("status_code", [450, 550])
    def test_unregister_service_client_err(self, status_code):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps({'notid': 'bla'})
        response_mock.status = status_code
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(client_exceptions.MicroserviceManagementClientError) as excinfo:
                    ret_value = ms_mgt_client.unregister_service('someid')

    def test_register_interest_good_id(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps({'id': 'bla'})
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.register_interest('cat', 'msid')
        request_patch.assert_called_once_with(
            body='{"category": "cat", "service": "msid"}', method='POST', url='/foglamp/interest')
        assert ret_value == {'id': 'bla'}

    def test_register_interest_no_id(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps({'notid': 'bla'})
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(KeyError) as excinfo:
                    ms_mgt_client.register_interest('cat', 'msid')

    @pytest.mark.parametrize("status_code", [450, 550])
    def test_register_interest_status_client_err(self, status_code):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        response_mock.status = status_code
        response_mock.reason = 'this is the reason'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(client_exceptions.MicroserviceManagementClientError) as excinfo:
                    ms_mgt_client.register_interest('cat', 'msid')

    def test_unregister_interest_good_id(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps({'id': 'bla'})
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.unregister_interest('someid')
        request_patch.assert_called_once_with(
            method='DELETE', url='/foglamp/interest/someid')

    def test_unregister_interest_no_id(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps({'notid': 'bla'})
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(KeyError) as excinfo:
                    ret_value = ms_mgt_client.unregister_interest('someid')

    @pytest.mark.parametrize("status_code", [450, 550])
    def test_unregister_interest_client_err(self, status_code):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps({'notid': 'bla'})
        response_mock.status = status_code
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(client_exceptions.MicroserviceManagementClientError) as excinfo:
                    ret_value = ms_mgt_client.unregister_interest('someid')

    @pytest.mark.parametrize("name, type, url",
                             [('foo', None, '/foglamp/service?name=foo'),
                              (None, 'bar', '/foglamp/service?type=bar'),
                              ('foo', 'bar', '/foglamp/service?name=foo&type=bar')])
    def test_get_services_good(self, name, type, url):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps(
            {'services': 'bla'})
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.get_services(name, type)
        request_patch.assert_called_once_with(
            method='GET', url=url)
        assert ret_value == {'services': 'bla'}

    def test_get_services_no_services(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps(
            {'notservices': 'bla'})
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(KeyError) as excinfo:
                    ret_value = ms_mgt_client.get_services('foo', 'bar')

    @pytest.mark.parametrize("status_code", [450, 550])
    def test_get_services_client_err(self, status_code):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps(
            {'services': 'bla'})
        response_mock.status = status_code
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(client_exceptions.MicroserviceManagementClientError) as excinfo:
                    ret_value = ms_mgt_client.get_services('foo', 'bar')

    def test_get_configuration_category(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        test_dict = {
            'ping_timeout': {
                'type': 'integer',
                'description': 'Timeout for a response from any given micro-service. (must be greater than 0)',
                'value': '1',
                'default': '1'},
            'sleep_interval': {
                'type': 'integer',
                'description': 'The time (in seconds) to sleep between health checks. (must be greater than 5)',
                'value': '5', 'default': '5'
            }
        }

        undecoded_data_mock.decode.return_value = json.dumps(test_dict)
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.get_configuration_category("SMNTR")
        request_patch.assert_called_once_with(method='GET', url='/foglamp/service/category/SMNTR')
        assert ret_value == test_dict

    @pytest.mark.parametrize("status_code", [450, 550])
    def test_get_configuration_category_exception(self, status_code):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        response_mock.status = status_code
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(client_exceptions.MicroserviceManagementClientError) as excinfo:
                    ret_value = ms_mgt_client.get_configuration_category("SMNTR")

    def test_get_configuration_item(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        test_dict = {
                'type': 'integer',
                'description': 'Timeout for a response from any given micro-service. (must be greater than 0)',
                'value': '1',
                'default': '1'
        }

        undecoded_data_mock.decode.return_value = json.dumps(test_dict)
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.get_configuration_item("SMNTR", "ping_timeout")
        request_patch.assert_called_once_with(method='GET', url='/foglamp/service/category/SMNTR/ping_timeout')
        assert ret_value == test_dict

    @pytest.mark.parametrize("status_code", [450, 550])
    def test_get_configuration_item_exception(self, status_code):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        response_mock.status = status_code
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(client_exceptions.MicroserviceManagementClientError) as excinfo:
                    ret_value = ms_mgt_client.get_configuration_item("SMNTR", "ping_timeout")

    def test_create_configuration_category(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        test_dict = {
            'key': 'TEST',
            'description': 'description',
            'value': {
                'ping_timeout': {
                    'type': 'integer',
                    'description': 'Timeout for a response from any given micro-service. (must be greater than 0)',
                    'value': '1',
                    'default': '1'},
                'sleep_interval': {
                    'type': 'integer',
                    'description': 'The time (in seconds) to sleep between health checks. (must be greater than 5)',
                    'value': '5',
                    'default': '5'
                }
            },
            'keep_original_items': False
        }

        undecoded_data_mock.decode.return_value = json.dumps(test_dict)
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.create_configuration_category(test_dict)
        request_patch.assert_called_once_with(method='POST', url='/foglamp/service/category', body=test_dict)
        assert ret_value == test_dict

    @pytest.mark.parametrize("status_code", [450, 550])
    def test_create_configuration_category_exception(self, status_code):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        test_dict = {
            'key': 'TEST',
            'description': 'description',
            'value': {
                'ping_timeout': {
                    'type': 'integer',
                    'description': 'Timeout for a response from any given micro-service. (must be greater than 0)',
                    'value': '1',
                    'default': '1'},
                'sleep_interval': {
                    'type': 'integer',
                    'description': 'The time (in seconds) to sleep between health checks. (must be greater than 5)',
                    'value': '5',
                    'default': '5'
                }
            },
            'keep_original_items': False
        }

        undecoded_data_mock.decode.return_value = json.dumps(test_dict)
        response_mock.read.return_value = undecoded_data_mock
        response_mock.status = status_code
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(client_exceptions.MicroserviceManagementClientError) as excinfo:
                    ret_value = ms_mgt_client.create_configuration_category(test_dict)

    def test_update_configuration_item(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        test_dict = {'value': '5'}

        undecoded_data_mock.decode.return_value = json.dumps(test_dict)
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.update_configuration_item("TEST", "blah", test_dict)
        request_patch.assert_called_once_with(method='PUT', url='/foglamp/service/category/TEST/blah', body=test_dict)
        assert ret_value == test_dict

    @pytest.mark.parametrize("status_code", [450, 550])
    def test_update_configuration_item_exception(self, status_code):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        test_dict = {'value': '5'}

        response_mock.status = status_code
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(client_exceptions.MicroserviceManagementClientError) as excinfo:
                    ret_value = ms_mgt_client.update_configuration_item("TEST", "blah", test_dict)

    def test_delete_configuration_item(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        test_dict = {'value': ''}

        undecoded_data_mock.decode.return_value = json.dumps(test_dict)
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.delete_configuration_item("TEST", "blah")
        request_patch.assert_called_once_with(method='DELETE', url='/foglamp/service/category/TEST/blah/value')
        assert ret_value == test_dict

    @pytest.mark.parametrize("status_code", [450, 550])
    def test_delete_configuration_item_exception(self, status_code):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        response_mock.status = status_code
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with pytest.raises(client_exceptions.MicroserviceManagementClientError) as excinfo:
                    ret_value = ms_mgt_client.delete_configuration_item("TEST", "blah")

