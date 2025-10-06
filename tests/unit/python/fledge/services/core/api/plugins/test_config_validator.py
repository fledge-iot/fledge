# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
import pytest
from unittest.mock import patch, AsyncMock
from aiohttp import web
from fledge.services.core import routes
from fledge.services.core.api.plugins.config_validator import ConfigurationValidator

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2025 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestConfigurationValidator:

    @pytest.fixture
    def client(self, aiohttp_client, loop):
        app = web.Application()
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(aiohttp_client(app))

    
    async def test_bad_json_payload(self, client):
        config = 1
        resp = await client.put('/fledge/plugin/validate', data=json.dumps(config))
        assert 400 == resp.status
        assert "Configuration data must be a JSON object" == resp.reason


    @pytest.mark.parametrize("config", [
        {},
        {"plugin": {"description": "Dummy Plugin", "type": "string", "default": "dummy", "readonly": "true"}}
    ])
    async def test_no_config_check_performed(self, client, config):
        resp = await client.put('/fledge/plugin/validate', data=json.dumps(config))
        assert 204 == resp.status
        assert "No Content" == resp.reason

    @pytest.mark.parametrize("config, ping_result, listening_result, expected_host_result, expected_listening_result", [
        # Host reachable, port listening (both pass)
        ({"plugin": {"description": "MQTT Plugin", "type": "string", "default": "mqtt", "readonly": "true"}, 
          "brokerHost": {"type": "string", "default": "mqtt.example.com", "value": "mqtt.example.com"}, 
          "brokerPort": {"type": "integer", "default": "1883", "value": "1883"}},
          (True, "Host 'mqtt.example.com' is reachable"),
          (True, "Service is listening on port 1883"),
          "pass", "pass"),
        
        # Host unreachable, port not listening (both fail)
        ({"plugin": {"description": "Modbus Plugin", "type": "string", "default": "modbus", "readonly": "true"}, 
          "address": {"description": "Modbus server address", "type": "string", "default": "unreachable.host.com"}, 
          "port": {"description": "Modbus port", "type": "integer", "default": "502"}},
          (False, "Host 'unreachable.host.com' appears to be unreachable - no response on common ports (80, 443, 22, 53)"),
          (False, "Connection to unreachable.host.com:502 timed out after 5 seconds"),
          "fail", "fail"),
        
        # Host reachable, port not listening (mixed result)
        ({"plugin": {"description": "HTTP Plugin", "type": "string", "default": "http", "readonly": "true"}, 
          "ServerHostname": {"type": "string", "default": "example.com"}, 
          "ServerPort": {"type": "integer", "default": "8080"}},
          (True, "Host 'example.com' is reachable"),
          (False, "No service is listening on example.com:8080"),
          "pass", "fail"),
        
        # DNS resolution failure
        ({"plugin": {"description": "OPC UA Plugin", "type": "string", "default": "opcua", "readonly": "true"}, 
          "url": {"type": "string", "default": "opc.tcp://invalid.hostname.xyz:4840/server"}},
          (False, "Cannot resolve hostname 'invalid.hostname.xyz' - please check the hostname is correct"),
          (False, "DNS lookup failed for 'invalid.hostname.xyz'"),
          "fail", "fail"),
        
        # Connection timeout scenario
        ({"plugin": {"description": "Database Plugin", "type": "string", "default": "database", "readonly": "true"}, 
          "host": {"type": "string", "default": "slow.database.com"}, 
          "port": {"type": "integer", "default": "5432"}},
          (False, "Connection test to 'slow.database.com' timed out - host may be unreachable"),
          (False, "Connection to slow.database.com:5432 timed out after 5 seconds"),
          "fail", "fail"),
        
        # Broker URL scenario
        ({"plugin": {"description": "MQTT Sparkplug Plugin", "type": "string", "default": "mqtt-sparkplug", "readonly": "true"}, 
          "broker": {"type": "string", "default": "tcp://broker.hivemq.com:1883"}},
          (True, "Host 'broker.hivemq.com' is reachable"),
          (True, "Service is listening on port 1883"),
          "pass", "pass")
    ])
    async def test_validate_configuration(self, client, config, ping_result, listening_result, expected_host_result, expected_listening_result):
        with patch.object(ConfigurationValidator, 'ping_host', new_callable=AsyncMock) as mock_ping, \
             patch.object(ConfigurationValidator, 'check_port_listening', new_callable=AsyncMock) as mock_listening:
            
            # Configure mock returns
            mock_ping.return_value = ping_result
            mock_listening.return_value = listening_result
            
            # Make the API call
            resp = await client.put('/fledge/plugin/validate', data=json.dumps(config))
            assert 200 == resp.status
            
            result = await resp.text()
            json_response = json.loads(result)
            
            # Verify HostReachable test results
            assert 'HostReachable' in json_response
            assert json_response['HostReachable']['description'] == 'Host Reachability'
            assert json_response['HostReachable']['result'] == expected_host_result
            
            # Check for detail on failed host reachable
            if expected_host_result == "fail":
                assert 'detail' in json_response['HostReachable']
                assert json_response['HostReachable']['detail']['reason'] == ping_result[1]
            
            # Verify Listening test results
            assert 'Listening' in json_response
            assert json_response['Listening']['description'] == 'Listening'
            assert json_response['Listening']['result'] == expected_listening_result
            
            # Check for detail on failed listening
            if expected_listening_result == "fail":
                assert 'detail' in json_response['Listening']
                assert json_response['Listening']['detail']['reason'] == listening_result[1]
            
            # Verify mocks were called
            assert mock_ping.called
            if any(field in str(config).lower() for field in ['port', 'url']) or \
               any('address' in str(config).lower() for _ in [1]):  # Address-only configs get default ports
                assert mock_listening.called

    @pytest.mark.parametrize("config, ping_result, listening_result, expected_host_result, expected_listening_result, config_type", [
        # a) Default KV pair only - uses default value
        ({"plugin": {"description": "Default Only Plugin", "type": "string", "default": "default-only", "readonly": "true"}, 
          "address": {"description": "Server address", "type": "string", "default": "default.example.com"}, 
          "port": {"description": "Server port", "type": "integer", "default": "8080"}},
          (True, "Host 'default.example.com' is reachable"),
          (False, "No service is listening on default.example.com:8080"),
          "pass", "fail", "default_only"),
        
        # b) Value KV pair only - uses value (no default)
        ({"plugin": {"description": "Value Only Plugin", "type": "string", "default": "value-only", "readonly": "true"}, 
          "hostname": {"description": "Server hostname", "type": "string", "value": "value.example.com"}, 
          "port": {"description": "Server port", "type": "integer", "value": "9090"}},
          (True, "Host 'value.example.com' is reachable"),
          (True, "Service is listening on port 9090"),
          "pass", "pass", "value_only"),
        
        # c) Both default and value KV pairs - value takes precedence over default
        ({"plugin": {"description": "Both Keys Plugin", "type": "string", "default": "both-keys", "readonly": "true"}, 
          "ServerHostname": {"description": "Server hostname", "type": "string", "default": "default.server.com", "value": "override.server.com"}, 
          "ServerPort": {"description": "Server port", "type": "integer", "default": "3000", "value": "4000"}},
          (False, "Host 'override.server.com' appears to be unreachable - no response on common ports (80, 443, 22, 53)"),
          (False, "Connection to override.server.com:4000 timed out after 5 seconds"),
          "fail", "fail", "both_keys_value_precedence"),
        
        # d) Default and value with URL field - value takes precedence
        ({"plugin": {"description": "URL Override Plugin", "type": "string", "default": "url-override", "readonly": "true"}, 
          "url": {"description": "Service URL", "type": "string", "default": "http://default.service.com:8080", "value": "https://custom.service.com:8443"}},
          (True, "Host 'custom.service.com' is reachable"),
          (True, "Service is listening on port 8443"),
          "pass", "pass", "url_value_precedence"),
        
        # e) Broker field with default only
        ({"plugin": {"description": "Broker Default Plugin", "type": "string", "default": "broker-default", "readonly": "true"}, 
          "broker": {"description": "MQTT Broker", "type": "string", "default": "tcp://default.broker.com:1883"}},
          (False, "Cannot resolve hostname 'default.broker.com' - please check the hostname is correct"),
          (False, "DNS lookup failed for 'default.broker.com'"),
          "fail", "fail", "broker_default_only"),
        
        # f) Mixed fields - some with default, some with value
        ({"plugin": {"description": "Mixed Fields Plugin", "type": "string", "default": "mixed", "readonly": "true"}, 
          "brokerHost": {"description": "Broker hostname", "type": "string", "value": "mixed.broker.com"}, 
          "brokerPort": {"description": "Broker port", "type": "integer", "default": "1883"}},
          (True, "Host 'mixed.broker.com' is reachable"),
          (False, "No service is listening on mixed.broker.com:1883"),
          "pass", "fail", "mixed_default_value"),
        
    ])
    async def test_configuration_key_value_patterns(self, client, config, ping_result, listening_result, 
                                                   expected_host_result, expected_listening_result, config_type):
        """Test different configuration key-value patterns: default only, value only, and both default+value."""
        
        with patch.object(ConfigurationValidator, 'ping_host', new_callable=AsyncMock) as mock_ping, \
             patch.object(ConfigurationValidator, 'check_port_listening', new_callable=AsyncMock) as mock_listening:
            
            # Configure mock returns
            mock_ping.return_value = ping_result
            mock_listening.return_value = listening_result
            
            # Make the API call
            resp = await client.put('/fledge/plugin/validate', data=json.dumps(config))
            assert 200 == resp.status
            
            result = await resp.text()
            json_response = json.loads(result)
            
            # Verify HostReachable test results
            assert 'HostReachable' in json_response
            assert json_response['HostReachable']['result'] == expected_host_result
            
            # Verify Listening test results  
            assert 'Listening' in json_response
            assert json_response['Listening']['result'] == expected_listening_result
            
            # Verify the correct values are being used based on config type
            host_values = json_response['HostReachable']['values'][0]
            listening_values = json_response['Listening']['values'][0]
            
            if config_type == "default_only":
                # Should use default values
                assert 'address' in host_values
                assert 'address' in listening_values and 'port' in listening_values
                
            elif config_type == "value_only":
                # Should use value fields
                assert 'hostname' in host_values
                assert 'hostname' in listening_values and 'port' in listening_values
                
            elif config_type == "both_keys_value_precedence":
                # Value should take precedence over default
                assert 'ServerHostname' in host_values
                assert 'ServerHostname' in listening_values and 'ServerPort' in listening_values
                # Verify the value field was used, not default
                mock_ping.assert_called_with('override.server.com')
                
            elif config_type == "url_value_precedence":
                # URL value should take precedence
                assert 'url' in host_values
                mock_ping.assert_called_with('custom.service.com')
                
            elif config_type == "broker_default_only":
                # Broker default should be used
                assert 'broker' in host_values
                mock_ping.assert_called_with('default.broker.com')
                
            elif config_type == "mixed_default_value":
                # Mixed: brokerHost uses value, brokerPort uses default
                assert 'brokerHost' in listening_values and 'brokerPort' in listening_values
                mock_ping.assert_called_with('mixed.broker.com')
                
            elif config_type == "address_value_override":
                # Address value should override default
                assert 'IP' in host_values
                mock_ping.assert_called_with('192.168.1.200')
            
            # Verify error details for failed tests
            if expected_host_result == "fail":
                assert 'detail' in json_response['HostReachable']
                assert json_response['HostReachable']['detail']['reason'] == ping_result[1]
                
            if expected_listening_result == "fail":
                assert 'detail' in json_response['Listening']
                assert json_response['Listening']['detail']['reason'] == listening_result[1]

    @pytest.mark.parametrize("config, expected_error_message", [
        # Test invalid URL format
        ({"plugin": {"description": "Invalid URL Plugin", "type": "string", "default": "invalid", "readonly": "true"}, 
          "url": {"type": "string", "default": "not-a-valid-url"}},
          "Invalid URL format 'not-a-valid-url' - please check the URL is correct"),
        
        # Test missing value and default
        ({"plugin": {"description": "Missing Value Plugin", "type": "string", "default": "missing", "readonly": "true"}, 
          "address": {"type": "string", "description": "Server address"}},
          "Configuration item 'address' must have either 'value' or 'default' key")
    ])
    async def test_validate_configuration_error_cases(self, client, config, expected_error_message):
        """Test configuration validation error handling without network calls."""
        
        resp = await client.put('/fledge/plugin/validate', data=json.dumps(config))
        
        if "Invalid URL format" in expected_error_message:
            # URL format errors return 200 with fail result
            assert 200 == resp.status
            result = await resp.text()
            json_response = json.loads(result)
            assert json_response['HostReachable']['result'] == 'fail'
            assert expected_error_message in json_response['HostReachable']['detail']['reason']
        else:
            # Missing value/default errors return 400
            assert 400 == resp.status
            assert expected_error_message in resp.reason

