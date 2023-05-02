# -*- coding: utf-8 -*-

from unittest.mock import MagicMock
from unittest.mock import patch
from http.client import HTTPConnection, HTTPResponse
import json
import pytest

from fledge.common.microservice_management_client import exceptions as client_exceptions
from fledge.common.microservice_management_client.microservice_management_client import MicroserviceManagementClient, _logger

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
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(
            body='{"keys": "vals"}', method='POST', url='/fledge/service')
        assert {'id': 'bla'} == ret_value

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
                with patch.object(_logger, "exception") as log_exc:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.register_service({})
                    assert excinfo.type is KeyError
                assert 1 == log_exc.call_count
                args = log_exc.call_args
                assert 'Could not register the microservice, From request {}'.format('{}') == args[0][1]
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(body='{}', method='POST', url='/fledge/service')

    @pytest.mark.parametrize("status_code, host", [(450, 'Client'), (550, 'Server')])
    def test_register_service_status_client_err(self, status_code, host):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        response_mock.status = status_code
        response_mock.reason = 'this is the reason'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.register_service({})
                    assert excinfo.type is client_exceptions.MicroserviceManagementClientError
                assert 1 == log_error.call_count
                msg = '{} error code: %d, Reason: %s'.format(host)
                log_error.assert_called_once_with(msg, status_code, 'this is the reason')
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(body='{}', method='POST', url='/fledge/service')

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
                ms_mgt_client.unregister_service('someid')
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='DELETE', url='/fledge/service/someid')

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
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.unregister_service('someid')
                    assert excinfo.type is KeyError
                assert 1 == log_error.call_count
                args = log_error.call_args
                assert 'Could not unregister the microservice having UUID {}'.format('someid') == args[0][1]
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='DELETE', url='/fledge/service/someid')

    @pytest.mark.parametrize("status_code, host", [(450, 'Client'), (550, 'Server')])
    def test_unregister_service_client_err(self, status_code, host):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps({'notid': 'bla'})
        response_mock.status = status_code
        response_mock.reason = 'this is the reason'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.unregister_service('someid')
                    assert excinfo.type is client_exceptions.MicroserviceManagementClientError
                assert 1 == log_error.call_count
                msg = '{} error code: %d, Reason: %s'.format(host)
                log_error.assert_called_once_with(msg, status_code, 'this is the reason')
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='DELETE', url='/fledge/service/someid')

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
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(
            body='{"category": "cat", "service": "msid"}', method='POST', url='/fledge/interest')
        assert {'id': 'bla'} == ret_value

    def test_register_interest_no_id(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps({'notid': 'bla'})
        response_mock.status = 200
        payload = '{"category": "cat", "service": "msid"}'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.register_interest('cat', 'msid')
                    assert excinfo.type is KeyError
                assert 1 == log_error.call_count
                args = log_error.call_args
                assert 'Could not register interest, for request payload {}'.format(payload) == args[0][1]
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(body=payload, method='POST', url='/fledge/interest')

    @pytest.mark.parametrize("status_code, host", [(450, 'Client'), (550, 'Server')])
    def test_register_interest_status_client_err(self, status_code, host):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        response_mock.status = status_code
        response_mock.reason = 'this is the reason'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.register_interest('cat', 'msid')
                    assert excinfo.type is client_exceptions.MicroserviceManagementClientError
                assert 1 == log_error.call_count
                msg = '{} error code: %d, Reason: %s'.format(host)
                log_error.assert_called_once_with(msg, status_code, 'this is the reason')
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(body='{"category": "cat", "service": "msid"}', method='POST',
                                              url='/fledge/interest')

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
                ms_mgt_client.unregister_interest('someid')
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='DELETE', url='/fledge/interest/someid')

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
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.unregister_interest('someid')
                    assert excinfo.type is KeyError
                assert 1 == log_error.call_count
                args = log_error.call_args
                assert 'Could not unregister interest for {}'.format('someid') == args[0][1]
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='DELETE', url='/fledge/interest/someid')

    @pytest.mark.parametrize("status_code, host", [(450, 'Client'), (550, 'Server')])
    def test_unregister_interest_client_err(self, status_code, host):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps({'notid': 'bla'})
        response_mock.status = status_code
        response_mock.reason = 'this is the reason'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.unregister_interest('someid')
                    assert excinfo.type is client_exceptions.MicroserviceManagementClientError
                assert 1 == log_error.call_count
                msg = '{} error code: %d, Reason: %s'.format(host)
                log_error.assert_called_once_with(msg, status_code, 'this is the reason')
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='DELETE', url='/fledge/interest/someid')

    @pytest.mark.parametrize("name, _type, url",
                             [('foo', None, '/fledge/service?name=foo'),
                              (None, 'bar', '/fledge/service?type=bar'),
                              ('foo', 'bar', '/fledge/service?name=foo&type=bar')])
    def test_get_services_good(self, name, _type, url):
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
                ret_value = ms_mgt_client.get_services(name, _type)
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='GET', url=url)
        assert {'services': 'bla'} == ret_value

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
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.get_services('foo', 'bar')
                    assert excinfo.type is KeyError
                assert 1 == log_error.call_count
                args = log_error.call_args
                assert 'Could not find the microservice for requested url {}'.format(
                    '/fledge/service?name=foo&type=bar') == args[0][1]
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='GET', url='/fledge/service?name=foo&type=bar')

    @pytest.mark.parametrize("status_code, host", [(450, 'Client'), (550, 'Server')])
    def test_get_services_client_err(self, status_code, host):
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
        response_mock.reason = 'this is the reason'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.get_services('foo', 'bar')
                        assert excinfo.type is client_exceptions.MicroserviceManagementClientError
                assert 1 == log_error.call_count
                msg = '{} error code: %d, Reason: %s'.format(host)
                log_error.assert_called_once_with(msg, status_code, 'this is the reason')
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='GET', url='/fledge/service?name=foo&type=bar')

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
                'description': 'Timeout for a response from any given microservice. (must be greater than 0)',
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
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='GET', url='/fledge/service/category/SMNTR')
        assert test_dict == ret_value

    @pytest.mark.parametrize("status_code, host", [(450, 'Client'), (550, 'Server')])
    def test_get_configuration_category_exception(self, status_code, host):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        response_mock.status = status_code
        response_mock.reason = 'this is the reason'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.get_configuration_category("SMNTR")
                    assert excinfo.type is client_exceptions.MicroserviceManagementClientError
                assert 1 == log_error.call_count
                msg = '{} error code: %d, Reason: %s'.format(host)
                log_error.assert_called_once_with(msg, status_code, 'this is the reason')
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='GET', url='/fledge/service/category/SMNTR')

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
                'description': 'Timeout for a response from any given microservice. (must be greater than 0)',
                'value': '1',
                'default': '1'
        }

        undecoded_data_mock.decode.return_value = json.dumps(test_dict)
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.get_configuration_item("SMNTR", "ping_timeout")
                assert test_dict == ret_value
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='GET', url='/fledge/service/category/SMNTR/ping_timeout')

    @pytest.mark.parametrize("status_code, host", [(450, 'Client'), (550, 'Server')])
    def test_get_configuration_item_exception(self, status_code, host):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        response_mock.status = status_code
        response_mock.reason = 'this is the reason'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.get_configuration_item("SMNTR", "ping_timeout")
                    assert excinfo.type is client_exceptions.MicroserviceManagementClientError
                assert 1 == log_error.call_count
                msg = '{} error code: %d, Reason: %s'.format(host)
                log_error.assert_called_once_with(msg, status_code, 'this is the reason')
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='GET', url='/fledge/service/category/SMNTR/ping_timeout')

    def test_create_configuration_category(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        test_dict = json.dumps({
            'key': 'TEST',
            'description': 'description',
            'value': {
                'ping_timeout': {
                    'type': 'integer',
                    'description': 'Timeout for a response from any given microservice. (must be greater than 0)',
                    'value': '1',
                    'default': '1'},
                'sleep_interval': {
                    'type': 'integer',
                    'description': 'The time (in seconds) to sleep between health checks. (must be greater than 5)',
                    'value': '5',
                    'default': '5'
                }
            }
        })

        undecoded_data_mock.decode.return_value = test_dict
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.create_configuration_category(test_dict)
                assert json.loads(test_dict) == ret_value
            response_patch.assert_called_once_with()
        args, kwargs = request_patch.call_args_list[0]
        assert 'POST' == kwargs['method']
        assert '/fledge/service/category' == kwargs['url']
        assert json.loads(test_dict) == json.loads(kwargs['body'])

    @pytest.mark.parametrize("status_code, host", [(450, 'Client'), (550, 'Server')])
    def test_create_configuration_category_exception(self, status_code, host):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        test_dict = json.dumps({
            'key': 'TEST',
            'description': 'description',
            'value': {
                'ping_timeout': {
                    'type': 'integer',
                    'description': 'Timeout for a response from any given microservice. (must be greater than 0)',
                    'value': '1',
                    'default': '1'},
                'sleep_interval': {
                    'type': 'integer',
                    'description': 'The time (in seconds) to sleep between health checks. (must be greater than 5)',
                    'value': '5',
                    'default': '5'
                }
            }
        })

        undecoded_data_mock.decode.return_value = test_dict
        response_mock.read.return_value = undecoded_data_mock
        response_mock.status = status_code
        response_mock.reason = 'this is the reason'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.create_configuration_category(test_dict)
                    assert excinfo.type is client_exceptions.MicroserviceManagementClientError
                assert 1 == log_error.call_count
                msg = '{} error code: %d, Reason: %s'.format(host)
                log_error.assert_called_once_with(msg, status_code, 'this is the reason')
            response_patch.assert_called_once_with()
        args, kwargs = request_patch.call_args_list[0]
        assert 'POST' == kwargs['method']
        assert '/fledge/service/category' == kwargs['url']
        assert json.loads(test_dict) == json.loads(kwargs['body'])

    def test_create_configuration_category_keep_original(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        test_dict = json.dumps({
            'key': 'TEST',
            'description': 'description',
            'value': {
                'ping_timeout': {
                    'type': 'integer',
                    'description': 'Timeout for a response from any given microservice. (must be greater than 0)',
                    'value': '1',
                    'default': '1'},
                'sleep_interval': {
                    'type': 'integer',
                    'description': 'The time (in seconds) to sleep between health checks. (must be greater than 5)',
                    'value': '5',
                    'default': '5'
                }
            },
            'keep_original_items': True
        })

        expected_test_dict = json.dumps({
            'key': 'TEST',
            'description': 'description',
            'value': {
                'ping_timeout': {
                    'type': 'integer',
                    'description': 'Timeout for a response from any given microservice. (must be greater than 0)',
                    'value': '1',
                    'default': '1'},
                'sleep_interval': {
                    'type': 'integer',
                    'description': 'The time (in seconds) to sleep between health checks. (must be greater than 5)',
                    'value': '5',
                    'default': '5'
                }
            }
        })
        undecoded_data_mock.decode.return_value = test_dict
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.create_configuration_category(test_dict)
                assert json.loads(test_dict) == ret_value
            response_patch.assert_called_once_with()
        args, kwargs = request_patch.call_args_list[0]
        assert 'POST' == kwargs['method']
        assert '/fledge/service/category?keep_original_items=true' == kwargs['url']
        assert json.loads(expected_test_dict) == json.loads(kwargs['body'])

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
                assert test_dict == ret_value
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='PUT', url='/fledge/service/category/TEST/blah', body=test_dict)

    @pytest.mark.parametrize("status_code, host", [(450, 'Client'), (550, 'Server')])
    def test_update_configuration_item_exception(self, status_code, host):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        test_dict = {'value': '5'}

        response_mock.status = status_code
        response_mock.reason = 'this is the reason'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.update_configuration_item("TEST", "blah", test_dict)
                    assert excinfo.type is client_exceptions.MicroserviceManagementClientError
                assert 1 == log_error.call_count
                msg = '{} error code: %d, Reason: %s'.format(host)
                log_error.assert_called_once_with(msg, status_code, 'this is the reason')
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(body={'value': '5'}, method='PUT',
                                              url='/fledge/service/category/TEST/blah')

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
                assert test_dict == ret_value
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='DELETE', url='/fledge/service/category/TEST/blah/value')

    @pytest.mark.parametrize("status_code, host", [(450, 'Client'), (550, 'Server')])
    def test_delete_configuration_item_exception(self, status_code, host):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        response_mock.status = status_code
        response_mock.reason = 'this is the reason'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.delete_configuration_item("TEST", "blah")
                    assert excinfo.type is client_exceptions.MicroserviceManagementClientError
                assert 1 == log_error.call_count
                msg = '{} error code: %d, Reason: %s'.format(host)
                log_error.assert_called_once_with(msg, status_code, 'this is the reason')
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='DELETE', url='/fledge/service/category/TEST/blah/value')

    def test_get_asset_tracker_event(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        test_dict = {
            "track": [
                {
                    "asset": "sinusoid",
                    "fledge": "Fledge",
                    "plugin": "sinusoid",
                    "service": "sine",
                    "timestamp": "2018-08-21 16:58:45.118",
                    "event": "Ingest"
                }
            ]
        }

        undecoded_data_mock.decode.return_value = json.dumps(test_dict)
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.get_asset_tracker_events()
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='GET', url='/fledge/track')
        assert test_dict == ret_value

    @pytest.mark.parametrize("status_code, host", [(450, 'Client'), (550, 'Server')])
    def test_get_asset_tracker_event_client_err(self, status_code, host):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        undecoded_data_mock.decode.return_value = json.dumps(
            {'track': []})
        response_mock.status = status_code
        response_mock.reason = 'this is the reason'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.get_asset_tracker_events()
                        assert excinfo.type is client_exceptions.MicroserviceManagementClientError
                assert 1 == log_error.call_count
                msg = '{} error code: %d, Reason: %s'.format(host)
                log_error.assert_called_once_with(msg, status_code, 'this is the reason')
            response_patch.assert_called_once_with()
        request_patch.assert_called_once_with(method='GET', url='/fledge/track')

    def test_create_asset_tracker_event(self):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        response_mock.read.return_value = undecoded_data_mock
        test_dict = json.dumps({
            'asset': 'AirIntake',
            'event': 'Ingest',
            'service': 'PT100_In1',
            'plugin': 'PT100'
        })

        undecoded_data_mock.decode.return_value = test_dict
        response_mock.status = 200
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                ret_value = ms_mgt_client.create_asset_tracker_event(test_dict)
                assert json.loads(test_dict) == ret_value
            response_patch.assert_called_once_with()
        args, kwargs = request_patch.call_args_list[0]
        assert 'POST' == kwargs['method']
        assert '/fledge/track' == kwargs['url']
        assert test_dict == json.loads(kwargs['body'])

    @pytest.mark.parametrize("status_code, host", [(450, 'Client'), (550, 'Server')])
    def test_create_asset_tracker_event_exception(self, status_code, host):
        microservice_management_host = 'host1'
        microservice_management_port = 1
        ms_mgt_client = MicroserviceManagementClient(
            microservice_management_host, microservice_management_port)
        response_mock = MagicMock(type=HTTPResponse)
        undecoded_data_mock = MagicMock()
        test_dict = json.dumps({
            'asset': 'AirIntake',
            'event': 'Ingest',
            'service': 'PT100_In1',
            'plugin': 'PT100'
        })
        undecoded_data_mock.decode.return_value = test_dict
        response_mock.read.return_value = undecoded_data_mock
        response_mock.status = status_code
        response_mock.reason = 'this is the reason'
        with patch.object(HTTPConnection, 'request') as request_patch:
            with patch.object(HTTPConnection, 'getresponse', return_value=response_mock) as response_patch:
                with patch.object(_logger, "error") as log_error:
                    with pytest.raises(Exception) as excinfo:
                        ms_mgt_client.create_asset_tracker_event(test_dict)
                    assert excinfo.type is client_exceptions.MicroserviceManagementClientError
                assert 1 == log_error.call_count
                msg = '{} error code: %d, Reason: %s'.format(host)
                log_error.assert_called_once_with(msg, status_code, 'this is the reason')
            response_patch.assert_called_once_with()
        args, kwargs = request_patch.call_args_list[0]
        assert 'POST' == kwargs['method']
        assert '/fledge/track' == kwargs['url']
        assert test_dict == json.loads(kwargs['body'])
