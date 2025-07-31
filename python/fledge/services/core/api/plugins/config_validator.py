# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import asyncio
import json
import socket
import re
from urllib.parse import urlparse
from aiohttp import web

from fledge.common.logger import FLCoreLogger

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2025 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = FLCoreLogger().get_logger(__name__)

_help = """
    ------------------------------------------------------------------------------
    | PUT                 | /fledge/plugin/validate                              |
    ------------------------------------------------------------------------------
"""

class ConfigurationValidator:
    """
    Configuration Validation System
    
    Provides connectivity validation for plugin configurations
    through ICMP ping tests and TCP connection attempts.
    """
    
    # Configuration item names to check (case insensitive)
    ADDRESS_FIELDS = ['address', 'ip', 'server', 'host', 'hostname']
    URL_FIELDS = ['url']
    BROKER_FIELDS = ['broker', 'brokerhost']
    PORT_FIELDS = ['port', 'brokerport']
    
    # Standard protocol ports
    STANDARD_PORTS = {
        'http': 80,
        'https': 443,
        'ftp': 21,
        'ssh': 22,
        'telnet': 23,
        'smtp': 25,
        'dns': 53,
        'dhcp': 67,
        'tftp': 69,
        'pop3': 110,
        'imap': 143,
        'snmp': 161,
        'ldap': 389,
        'ldaps': 636,
        'mqtt': 1883,
        'mqtts': 8883,
        'opcua': 4840,
        'modbus': 502,
        'bacnet': 47808,
        'coap': 5683,
        'coaps': 5684
    }
    
    def __init__(self):
        self.results = {}
    
    def extract_configuration_items(self, config_data):
        """
        Extract relevant configuration items for validation.
        
        Args:
            config_data (dict): Configuration category contents
            
        Returns:
            dict: Categorized configuration items
            
        Raises:
            ValueError: If configuration item has neither 'value' nor 'default' key
        """
        extracted = {
            'addresses': [],
            'urls': [],
            'brokers': [],
            'ports': []
        }
        
        if not isinstance(config_data, dict):
            return extracted
            
        for key, value in config_data.items():
            if not isinstance(value, dict):
                continue
            
            # Check for value first, then default, then error
            config_value = None
            if 'value' in value:
                config_value = str(value['value']).strip()
            elif 'default' in value:
                config_value = str(value['default']).strip()
            else:
                raise ValueError(f"Configuration item '{key}' must have either 'value' or 'default' key")
            
            # Skip empty or zero values
            if not config_value or config_value == '0':
                continue
                
            key_lower = key.lower()
            field_type = value.get('type', 'string').lower()
            
            # Check for port fields first (more specific)
            if any(field in key_lower for field in self.PORT_FIELDS):
                try:
                    port_val = int(config_value)
                    if port_val > 0:
                        extracted['ports'].append({
                            'name': key,
                            'value': port_val,
                            'type': value.get('type', 'integer')
                        })
                except ValueError:
                    pass
            
            # Check for URL fields
            elif any(field in key_lower for field in self.URL_FIELDS):
                extracted['urls'].append({
                    'name': key,
                    'value': config_value,
                    'type': value.get('type', 'string')
                })
            
            # Check for broker fields
            elif any(field in key_lower for field in self.BROKER_FIELDS):
                extracted['brokers'].append({
                    'name': key,
                    'value': config_value,
                    'type': value.get('type', 'string')
                })
            
            # Check for address fields (less specific, checked last)
            # Exclude certain types that are not network addresses
            elif (any(field in key_lower for field in self.ADDRESS_FIELDS) and 
                  field_type not in ['enumeration', 'password', 'boolean']):
                extracted['addresses'].append({
                    'name': key,
                    'value': config_value,
                    'type': value.get('type', 'string')
                })
                    
        return extracted
    
    def parse_url(self, url_string):
        """
        Parse URL to extract hostname and port.
        
        Args:
            url_string (str): URL to parse
            
        Returns:
            tuple: (hostname, port, protocol) or (None, None, None) if invalid
        """
        try:
            # Handle special protocols like opc.tcp and tcp (MQTT)
            if url_string.startswith('opc.tcp://'):
                url_string = url_string.replace('opc.tcp://', 'opcua://')
            elif url_string.startswith('tcp://'):
                # Convert tcp:// to mqtt:// for standard parsing
                url_string = url_string.replace('tcp://', 'mqtt://')
            
            parsed = urlparse(url_string)
            
            if not parsed.hostname:
                return None, None, None
                
            hostname = parsed.hostname
            port = parsed.port
            protocol = parsed.scheme.lower()
            
            # Map back to original protocol names
            if protocol == 'opcua':
                protocol = 'opc.tcp'
            elif protocol == 'mqtt' and 'tcp://' in url_string:
                protocol = 'tcp'  # Original was tcp://

            # Use standard port if not specified
            if port is None and protocol in self.STANDARD_PORTS:
                port = self.STANDARD_PORTS[protocol]
            elif port is None and protocol == 'tcp':
                # Default MQTT port for tcp:// URLs
                port = self.STANDARD_PORTS['mqtt']
                
            return hostname, port, protocol
            
        except Exception as e:
            _logger.debug(f"URL parsing error for '{url_string}': {e}")
            return None, None, None
    
    def is_url(self, value):
        """
        Check if a value is a valid URL.
        
        Args:
            value (str): Value to check
            
        Returns:
            bool: True if value appears to be a URL
        """
        url_pattern = re.compile(
            r'^(https?|ftp|mqtt|mqtts|opcua|opc\.tcp|tcp|coap|coaps)://'
            r'[\w\-\.]+(:\d+)?(/.*)?$',
            re.IGNORECASE
        )
        return bool(url_pattern.match(value))
    
    async def ping_host(self, hostname):
        """
        Perform host reachability test using socket connection.
        
        This method uses socket-based connectivity testing instead of ICMP ping
        to work in containerized environments where ping may not be available.
        
        For Docker hostnames, this test simply validates DNS resolution since
        Docker internal hosts may only have specific services running.
        
        Args:
            hostname (str): Hostname or IP address to test
            
        Returns:
            tuple: (success, reason)
        """
        try:
            # First try to resolve the hostname
            _logger.debug(f"Attempting to resolve hostname: {hostname}")
            
            # Use getaddrinfo to resolve hostname and test connectivity
            import socket
            try:
                # Resolve hostname to IP addresses
                addr_info = await asyncio.get_event_loop().run_in_executor(
                    None, socket.getaddrinfo, hostname, None
                )
                
                if not addr_info:
                    return False, "Hostname could not be resolved"
                
                _logger.debug(f"Resolved {hostname} to {len(addr_info)} addresses")
                
                # Special handling for Docker internal hostnames
                if hostname in ['host.docker.internal', 'gateway.docker.internal'] or hostname.endswith('.docker.internal'):
                    _logger.debug(f"Docker hostname detected: {hostname}")
                    return True, f"Docker hostname '{hostname}' is resolvable and assumed reachable"
                
                # Special handling for localhost and loopback addresses - these are always considered reachable if they resolve
                if hostname.lower() in ['localhost', '127.0.0.1', '::1'] or hostname.startswith('127.'):
                    _logger.debug(f"Localhost/loopback address detected: {hostname}")
                    return True, f"Localhost address '{hostname}' is always reachable"

                # Try to connect to each resolved address on a common port
                # We'll try port 80 (HTTP) as it's commonly open and fast to test
                for family, socktype, proto, canonname, sockaddr in addr_info:
                    if family in (socket.AF_INET, socket.AF_INET6):
                        try:
                            # Extract IP address from sockaddr
                            ip_addr = sockaddr[0]
                            
                            # Test connectivity using a socket connection to port 80
                            # This is faster and more reliable than ping in containers
                            test_port = 80  # HTTP port - commonly accessible
                            
                            _logger.debug(f"Testing connectivity to {ip_addr}:{test_port}")
                            
                            # Create socket connection with short timeout
                            sock = socket.socket(family, socket.SOCK_STREAM)
                            sock.settimeout(3)  # 3 second timeout
                            
                            try:
                                result = await asyncio.get_event_loop().run_in_executor(
                                    None, sock.connect, (ip_addr, test_port)
                                )
                                sock.close()
                                _logger.debug(f"Successfully connected to {ip_addr}:{test_port}")
                                return True, f"Host '{hostname}' is reachable"
                                
                            except (socket.timeout, OSError) as conn_err:
                                sock.close()
                                _logger.debug(f"Connection to {ip_addr}:{test_port} failed: {conn_err}")
                                
                                # Try a few more common ports to increase success rate
                                for alt_port in [443, 22, 53]:  # HTTPS, SSH, DNS
                                    try:
                                        sock = socket.socket(family, socket.SOCK_STREAM)
                                        sock.settimeout(2)  # Shorter timeout for alt ports
                                        
                                        await asyncio.get_event_loop().run_in_executor(
                                            None, sock.connect, (ip_addr, alt_port)
                                        )
                                        sock.close()
                                        _logger.debug(f"Successfully connected to {ip_addr}:{alt_port}")
                                        return True, f"Host '{hostname}' is reachable"
                                        
                                    except (socket.timeout, OSError):
                                        sock.close()
                                        continue
                                
                                # If we get here, the host might be up but not responding on tested ports
                                # This is still considered "reachable" from a network perspective
                                continue
                        
                        except Exception as e:
                            _logger.debug(f"Error testing {ip_addr}: {e}")
                            continue
                
                # If we tried all addresses and none worked, the host is likely unreachable
                return False, f"Host '{hostname}' appears to be unreachable - no response on common ports (80, 443, 22, 53)"
                
            except socket.gaierror as e:
                error_msg = str(e).lower()
                _logger.error(f"DNS resolution failed for {hostname}: {e}")
                
                if 'name or service not known' in error_msg or 'nodename nor servname provided' in error_msg:
                    return False, f"Cannot resolve hostname '{hostname}' - please check the hostname is correct"
                elif 'temporary failure' in error_msg:
                    return False, f"Temporary DNS failure for '{hostname}' - please try again later"
                else:
                    return False, f"DNS lookup failed for '{hostname}'"
                    
        except asyncio.TimeoutError:
            _logger.warning(f"Host reachability test timed out for {hostname}")
            return False, f"Connection test to '{hostname}' timed out - host may be unreachable"
        except Exception as e:
            _logger.error(f"Unexpected error during host reachability test for {hostname}: {e}")
            return False, f"Cannot test reachability of '{hostname}' - network error occurred"
    
    async def check_port_listening(self, hostname, port):
        """
        Check if a service is listening on the specified host and port.
        
        Args:
            hostname (str): Hostname or IP address
            port (int): Port number
            
        Returns:
            tuple: (success, reason)
        """
        try:
            # Attempt TCP connection
            _logger.debug(f"Testing connection to {hostname}:{port}")
            future = asyncio.open_connection(hostname, port)
            reader, writer = await asyncio.wait_for(future, timeout=5.0)
            
            # Close the connection immediately
            writer.close()
            await writer.wait_closed()
            
            _logger.debug(f"Successfully connected to {hostname}:{port}")
            return True, f"Service is listening on port {port}"
        except asyncio.TimeoutError:
            _logger.warning(f"Connection timeout to {hostname}:{port}")
            return False, f"Connection to {hostname}:{port} timed out after 5 seconds"
        except ConnectionRefusedError:
            _logger.error(f"Connection refused by {hostname}:{port}")
            return False, f"No service is listening on {hostname}:{port}"
        except socket.gaierror as e:
            error_msg = str(e).lower()
            _logger.error(f"DNS resolution failed for {hostname}: {e}")
            
            if 'name or service not known' in error_msg or 'nodename nor servname provided' in error_msg:
                return False, f"Cannot resolve hostname '{hostname}' - please check the hostname is correct"
            elif 'temporary failure' in error_msg:
                return False, f"Temporary DNS failure for '{hostname}' - please try again later"
            else:
                return False, f"DNS lookup failed for '{hostname}'"
        except OSError as e:
            error_code = getattr(e, 'errno', None)
            error_msg = str(e).lower()
            _logger.error(f"Network error connecting to {hostname}:{port}: {e}")
            
            # Handle specific error codes for better user messages
            if error_code == 111 or 'connection refused' in error_msg:
                return False, f"No service is listening on {hostname}:{port}"
            elif error_code == 113 or 'no route to host' in error_msg:
                return False, f"Cannot reach host '{hostname}' - check network connectivity"
            elif error_code == 110 or 'connection timed out' in error_msg:
                return False, f"Connection to {hostname}:{port} timed out - host may be unreachable"
            elif 'network is unreachable' in error_msg:
                return False, f"Network unreachable to '{hostname}' - check network configuration"
            elif 'host is unreachable' in error_msg:
                return False, f"Host '{hostname}' is unreachable - check if host is online"
            elif 'multiple exceptions' in error_msg:
                # Handle IPv6/IPv4 dual stack connection failures
                return False, f"Cannot connect to {hostname}:{port} - no service available"
            else:
                return False, f"Network error connecting to {hostname}:{port}"
        except Exception as e:
            _logger.error(f"Unexpected error testing {hostname}:{port}: {e}")
            return False, f"Connection test failed for {hostname}:{port}"
    
    async def test_host_reachable(self, config_items):
        """
        Test host reachability using ICMP ping.
        
        Args:
            config_items (dict): Extracted configuration items
            
        Returns:
            dict: Test results
        """
        hosts_to_test = set()
        test_values = []
        
        # Process direct address fields
        for item in config_items['addresses']:
            hosts_to_test.add(item['value'])
            test_values.append({item['name']: item['value']})
        
        # Process URLs
        for item in config_items['urls']:
            hostname, _, _ = self.parse_url(item['value'])
            if hostname:
                hosts_to_test.add(hostname)
                test_values.append({item['name']: item['value']})
            else:
                return {
                    "description": "Host Reachable",
                    "result": "fail",
                    "detail": {"reason": f"Invalid URL format '{item['value']}' - please check the URL is correct"},
                    "values": [{item['name']: item['value']}]
                }
        
        # Process brokers
        for item in config_items['brokers']:
            if self.is_url(item['value']):
                # Broker is a URL
                hostname, _, _ = self.parse_url(item['value'])
                if hostname:
                    hosts_to_test.add(hostname)
                    test_values.append({item['name']: item['value']})
                else:
                    return {
                        "description": "Host Reachable",
                        "result": "fail",
                        "detail": {"reason": f"Invalid URL format '{item['value']}' - please check the URL is correct"},
                        "values": [{item['name']: item['value']}]
                    }
            else:
                # Broker is hostname only or brokerHost
                hostname = item['value']
                hosts_to_test.add(hostname)
                test_values.append({item['name']: item['value']})
        
        if not hosts_to_test:
            return None  # No applicable tests
        
        # Test all unique hosts
        all_passed = True
        failure_reason = None
        
        for hostname in hosts_to_test:
            success, reason = await self.ping_host(hostname)
            if not success:
                all_passed = False
                failure_reason = reason
                break
        
        result = {
            "description": "Host Reachable",
            "result": "pass" if all_passed else "fail",
            "values": test_values
        }
        
        if not all_passed:
            result["detail"] = {"reason": failure_reason}
            
        return result
    
    async def test_listening(self, config_items):
        """
        Test if services are listening on specified ports.
        
        Args:
            config_items (dict): Extracted configuration items
            
        Returns:
            dict: Test results
        """
        connections_to_test = []
        test_values = []
        processed_combinations = set()  # Track processed host:port combinations to avoid duplicates
        
        # Handle separated broker host/port fields first (most specific)
        broker_hosts = [item for item in config_items['brokers'] if 'host' in item['name'].lower()]
        broker_ports = [item for item in config_items['ports'] if 'broker' in item['name'].lower()]

        # Pair broker hosts with broker ports
        for host_item in broker_hosts:
            hostname = host_item['value']
            port = None
            
            # Find corresponding broker port
            for port_item in broker_ports:
                port = port_item['value']
                combination_key = f"{hostname}:{port}"
                if combination_key not in processed_combinations:
                    # Combine broker host and port into single object
                    test_values.append({
                        host_item['name']: hostname,
                        port_item['name']: str(port)
                    })
                    connections_to_test.append((hostname, port))
                    processed_combinations.add(combination_key)
                break
            
            if not port:
                # Use MQTT defaults if no broker port found
                for default_port in [1883, 8883]:  # MQTT, MQTTS
                    combination_key = f"{hostname}:{default_port}"
                    if combination_key not in processed_combinations:
                        connections_to_test.append((hostname, default_port))
                        processed_combinations.add(combination_key)

                test_values.append({
                    host_item['name']: hostname,
                    "default_ports": "1883,8883"
                })
        
        # Process broker URLs
        for item in config_items['brokers']:
            if self.is_url(item['value']):
                # Broker is a URL
                hostname, port, protocol = self.parse_url(item['value'])
                if hostname and port:
                    combination_key = f"{hostname}:{port}"
                    if combination_key not in processed_combinations:
                        connections_to_test.append((hostname, port))
                        test_values.append({item['name']: item['value']})
                        processed_combinations.add(combination_key)
            else:
                # Broker is hostname only (check if not already processed by broker host/port logic)
                if not any('host' in broker['name'].lower() for broker in config_items['brokers']):
                    hostname = item['value']
                    port = None

                    # Look for a corresponding port field
                    for port_item in config_items['ports']:
                        # Skip broker-specific ports as they're handled separately
                        if 'broker' not in port_item['name'].lower():
                            port = port_item['value']
                            combination_key = f"{hostname}:{port}"
                            if combination_key not in processed_combinations:
                                # Combine broker and port into single object
                                test_values.append({
                                    item['name']: item['value'],
                                    port_item['name']: str(port)
                                })
                                connections_to_test.append((hostname, port))
                                processed_combinations.add(combination_key)
                            break

                    # If no explicit port, use MQTT defaults
                    if port is None:
                        # Try both standard MQTT ports
                        for default_port in [1883, 8883]:  # MQTT, MQTTS
                            combination_key = f"{hostname}:{default_port}"
                            if combination_key not in processed_combinations:
                                connections_to_test.append((hostname, default_port))
                                processed_combinations.add(combination_key)

                        test_values.append({
                            item['name']: item['value'],
                            "default_ports": "1883,8883"
                        })

        # Process URLs with ports
        for item in config_items['urls']:
            hostname, port, protocol = self.parse_url(item['value'])
            if hostname and port:
                combination_key = f"{hostname}:{port}"
                if combination_key not in processed_combinations:
                    connections_to_test.append((hostname, port))
                    test_values.append({item['name']: item['value']})
                    processed_combinations.add(combination_key)

        # Handle standard address + port combinations (skip if broker processing already handled them)
        if config_items['ports'] and not broker_hosts:
            port_item = config_items['ports'][0]  # Use first port found
            port = port_item['value']

            # Look for corresponding address
            address = None
            for item in config_items['addresses']:
                address = item['value']
                combination_key = f"{address}:{port}"
                if combination_key not in processed_combinations:
                    # Combine address and port into single object
                    test_values.append({
                        item['name']: item['value'],
                        port_item['name']: str(port)
                    })
                    connections_to_test.append((address, port))
                    processed_combinations.add(combination_key)
                break

        # Handle addresses without ports (like S7, EtherIP) - use common protocol ports
        if not connections_to_test and config_items['addresses']:
            for address_item in config_items['addresses']:
                hostname = address_item['value']

                # Try common protocol ports based on field names only
                field_name = address_item['name'].lower()
                default_ports = []

                if 'ip' in field_name:
                    # IP fields often used for industrial protocols
                    default_ports = [102, 44818, 502, 80, 443]  # S7, EtherNet/IP, Modbus, HTTP, HTTPS
                elif 'address' in field_name:
                    # Address fields commonly used for network services
                    default_ports = [502, 80, 443]  # Modbus, HTTP, HTTPS
                elif 'host' in field_name or 'server' in field_name:
                    # Host/server fields typically web services
                    default_ports = [80, 443]  # HTTP, HTTPS
                else:
                    # Generic network address
                    default_ports = [80, 443]  # HTTP, HTTPS

                for default_port in default_ports:
                    combination_key = f"{hostname}:{default_port}"
                    if combination_key not in processed_combinations:
                        connections_to_test.append((hostname, default_port))
                        processed_combinations.add(combination_key)

                test_values.append({
                    address_item['name']: hostname,
                    "default_ports": ",".join(map(str, default_ports))
                })
                break  # Only process first address to avoid duplicates
        
        if not connections_to_test:
            return None  # No applicable tests
        
        # Test all connections
        all_passed = True
        failure_reason = None
        
        for hostname, port in connections_to_test:
            success, reason = await self.check_port_listening(hostname, port)
            if not success:
                all_passed = False
                failure_reason = reason
                break
        
        result = {
            "description": "Listening",
            "result": "pass" if all_passed else "fail",
            "values": test_values
        }
        
        if not all_passed:
            result["detail"] = {"reason": failure_reason}
            
        return result
    
    async def validate_configuration(self, config_data):
        """
        Validate plugin configuration by running all applicable tests.
        
        Args:
            config_data (dict): Plugin configuration category contents
            
        Returns:
            dict: Validation results
        """
        self.results = {}
        
        # Extract configuration items
        config_items = self.extract_configuration_items(config_data)
        
        # Run host reachability test
        host_result = await self.test_host_reachable(config_items)
        if host_result:
            self.results["HostReachable"] = host_result
        
        # Run listening test
        listening_result = await self.test_listening(config_items)
        if listening_result:
            self.results["Listening"] = listening_result
        
        return self.results


async def validate_configuration(request):
    """
    API endpoint for plugin configuration validation.
    
    PUT /fledge/plugin/validate
    
    Validates connectivity aspects of plugin configurations.
    """
    try:
        data = await request.json()
        
        if not isinstance(data, dict):
            raise ValueError("Configuration data must be a JSON object")
        
        validator = ConfigurationValidator()
        results = await validator.validate_configuration(data)
        if not results:
            # No validation could be performed
            return web.Response(status=204)
        
        return web.json_response(results)
    except json.JSONDecodeError:
        raise web.HTTPBadRequest(reason="Invalid JSON payload")
    except ValueError as e:
        # This catches both general validation errors and missing value/default errors
        raise web.HTTPBadRequest(reason=str(e))
    except Exception as e:
        _logger.error(f"Plugin validation error: {e}")
        raise web.HTTPInternalServerError(reason="Internal server error during validation")

def setup(app):
    """Setup plugin validation routes"""
    app.router.add_route('PUT', '/fledge/plugin/validate', validate_configuration)

