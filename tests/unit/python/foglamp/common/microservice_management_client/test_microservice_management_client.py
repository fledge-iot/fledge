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
