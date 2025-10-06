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
    
    Provides connectivity validation for plugin configurations through:
    - ICMP ping tests for host reachability (preferred method)
    - TCP connection attempts for service availability
    - Automatic fallback to TCP connectivity testing in restricted container environments
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
    

    async def _icmp_ping(self, hostname, timeout=3):
        """
        Perform ICMP ping using system ping command.
        
        Args:
            hostname (str): Hostname or IP address to ping
            timeout (int): Timeout in seconds
            
        Returns:
            tuple: (success, reason) or (None, reason) if ICMP unavailable
        """
        try:
            import subprocess
            import asyncio
            
            # Use ping command with specific parameters for reliability
            # -c 1: send only 1 packet
            # -W timeout: wait timeout seconds for response
            # -q: quiet output (only summary)
            cmd = ['ping', '-c', '1', '-W', str(timeout), '-q', hostname]
            
            _logger.debug(f"Running ICMP ping: {' '.join(cmd)}")
            
            # Run ping command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout + 2  # Allow extra time for process cleanup
            )
            
            if process.returncode == 0:
                _logger.debug(f"ICMP ping to the host '{hostname}' successful")
                return True, f"Host '{hostname}' is reachable (ICMP ping successful)"
            else:
                # Parse ping output for better error messages
                stderr_str = stderr.decode('utf-8', errors='ignore').lower()
                stdout_str = stdout.decode('utf-8', errors='ignore').lower()
                combined_output = stderr_str + stdout_str
                
                if 'name or service not known' in combined_output or 'cannot resolve' in combined_output:
                    return False, f"Unable to resolve the hostname '{hostname}' - please check the hostname is correct"
                elif 'network is unreachable' in combined_output:
                    return False, f"Network unreachable to the hostname '{hostname}' - check network configuration"
                elif 'host unreachable' in combined_output or 'no route to host' in combined_output:
                    return False, f"Host '{hostname}' is unreachable - check if host is online and network path exists"
                elif '100% packet loss' in combined_output or 'no answer' in combined_output:
                    return False, f"Host '{hostname}' does not respond to ping - may be down or blocking ICMP"
                else:
                    return False, f"Host '{hostname}' ping failed - host may be unreachable or blocking ICMP"
                    
        except asyncio.TimeoutError:
            _logger.warning(f"ICMP ping to the host '{hostname}' timed out")
            return False, f"Ping to '{hostname}' timed out - host may be unreachable"
        except FileNotFoundError:
            _logger.debug("Ping command not found - falling back to TCP connectivity test")
            return None, "ICMP ping not available"
        except PermissionError:
            _logger.debug("Permission denied for ICMP ping - falling back to TCP connectivity test")
            return None, "ICMP ping not permitted"
        except Exception as e:
            _logger.debug(f"ICMP ping failed with error: {e}")
            return None, f"ICMP ping unavailable: {e}"

    async def _tcp_connectivity_test(self, hostname):
        """
        Test host connectivity using TCP socket connections.
        
        This method provides better error differentiation between host down 
        vs no service listening compared to the previous implementation.
        
        Args:
            hostname (str): Hostname or IP address to test
            
        Returns:
            tuple: (success, reason)
        """
        try:
            # First try to resolve the hostname
            _logger.debug(f"Attempting to resolve hostname: {hostname}")
            
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
                
                # Special handling for localhost and loopback addresses
                if hostname.lower() in ['localhost', '127.0.0.1', '::1'] or hostname.startswith('127.'):
                    _logger.debug(f"Localhost/loopback address detected: {hostname}")
                    return True, f"Localhost address '{hostname}' is always reachable"

                # Test connectivity to each resolved address
                connection_refused_count = 0
                timeout_count = 0
                total_attempts = 0
                host_unreachable_count = 0
                network_unreachable_count = 0
                
                # Improved port selection for better detection
                test_ports = [80, 443, 22, 53, 23, 21]  # HTTP, HTTPS, SSH, DNS, Telnet, FTP
                
                for family, socktype, proto, canonname, sockaddr in addr_info:
                    if family in (socket.AF_INET, socket.AF_INET6):
                        ip_addr = sockaddr[0]
                        
                        for test_port in test_ports:
                            total_attempts += 1
                            try:
                                _logger.debug(f"Testing connectivity to {ip_addr}:{test_port}")
                                
                                with socket.socket(family, socket.SOCK_STREAM) as sock:
                                    sock.settimeout(2)  # Short timeout for responsiveness
                                    
                                    await asyncio.get_event_loop().run_in_executor(
                                        None, sock.connect, (ip_addr, test_port)
                                    )
                                    
                                    _logger.debug(f"Successfully connected to {ip_addr}:{test_port}")
                                    return True, f"Host '{hostname}' is reachable (TCP connection successful)"
                                    
                            except (socket.timeout, asyncio.TimeoutError):
                                timeout_count += 1
                                _logger.debug(f"Connection to {ip_addr}:{test_port} timed out")
                                continue
                                
                            except ConnectionRefusedError:
                                connection_refused_count += 1
                                _logger.debug(f"Connection to {ip_addr}:{test_port} refused")
                                continue
                                
                            except OSError as e:
                                error_code = getattr(e, 'errno', None)
                                error_msg = str(e).lower()
                                
                                if error_code == 111 or 'connection refused' in error_msg:
                                    connection_refused_count += 1
                                elif error_code == 110 or 'timed out' in error_msg or 'timeout' in error_msg:
                                    timeout_count += 1
                                elif error_code == 113 or 'no route to host' in error_msg:
                                    host_unreachable_count += 1
                                elif 'network is unreachable' in error_msg:
                                    network_unreachable_count += 1
                                elif 'host is unreachable' in error_msg:
                                    host_unreachable_count += 1
                                else:
                                    timeout_count += 1  # Treat unknown errors as timeouts
                                continue
                                
                            except Exception as e:
                                _logger.debug(f"Unexpected error testing {ip_addr}:{test_port}: {e}")
                                timeout_count += 1
                                continue
                
                # Analyze results to provide better error messages based on network stack responses
                if network_unreachable_count > 0:
                    return False, f"Network unreachable to '{hostname}' - check network configuration"
                elif host_unreachable_count > 0:
                    return False, f"Host '{hostname}' is unreachable - check if host is online and network path exists"
                elif connection_refused_count == total_attempts:
                    # All connections refused - host is up but no tested services are running
                    return True, f"Host '{hostname}' is reachable but no common services are running on tested ports"
                elif timeout_count == total_attempts:
                    # All connections timed out - host is likely down or blocking connections
                    return False, f"Host '{hostname}' appears to be down or blocking connections (all connection attempts timed out)"
                elif connection_refused_count > 0:
                    # Some connections refused - host is likely up
                    return True, f"Host '{hostname}' is reachable (host responded with connection refused, indicating it's online)"
                else:
                    # No clear pattern - host is likely unreachable
                    return False, f"Host '{hostname}' appears to be unreachable - no successful connections established"
                
            except socket.gaierror as e:
                error_msg = str(e).lower()
                _logger.error(f"DNS resolution failed for the hostname '{hostname}': {e}")
                
                if 'name or service not known' in error_msg or 'nodename nor service name provided' in error_msg:
                    return False, f"Cannot resolve hostname '{hostname}' - please check the hostname is correct"
                elif 'temporary failure' in error_msg:
                    return False, f"Temporary DNS failure for '{hostname}' - please try again later"
                else:
                    return False, f"DNS lookup failed for '{hostname}'"
                    
        except Exception as e:
            _logger.error(f"Unexpected error during TCP connectivity test for the hostname '{hostname}': {e}")
            return False, f"Cannot test connectivity to the hostname '{hostname}' - network error occurred"

    async def ping_host(self, hostname):
        """
        Perform host reachability test using ICMP ping when available,
        falling back to TCP connectivity testing in restricted environments.
        
        This method tries ICMP ping first (most reliable and appropriate for host reachability),
        and only falls back to TCP socket testing when ICMP is not available due to
        container restrictions or permissions.
        
        Args:
            hostname (str): Hostname or IP address to test
            
        Returns:
            tuple: (success, reason)
        """
        try:
            
            # Try ICMP ping first
            icmp_result, icmp_reason = await self._icmp_ping(hostname)
            if icmp_result is not None:  # None means ICMP not available
                return icmp_result, icmp_reason
                    
            # Fall back to TCP connectivity test
            _logger.debug(f"Using TCP connectivity test for the hostname '{hostname}' (container environment: {in_container})")
            return await self._tcp_connectivity_test(hostname)
            
        except Exception as e:
            _logger.error(f"Unexpected error during host reachability test for the hostname '{hostname}': {e}")
            return False, f"Unable to test reachability of the hostname '{hostname}' - error occurred: {e}"
    
    async def check_port_listening(self, hostname, port, include_port_in_messages=True):
        """
        Check if a service is listening on the specified host and port.
        
        Args:
            hostname (str): Hostname or IP address
            port (int): Port number
            include_port_in_messages (bool): Whether to include port details in error messages
            
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
            success_msg = f"Service is listening on port {port}" if include_port_in_messages else f"Connection successfully established on {hostname}"
            return True, success_msg
        except asyncio.TimeoutError:
            _logger.warning(f"Connection timeout to {hostname}:{port}")
            error_msg = f"Connection to {hostname}:{port} timed out after 5 seconds" if include_port_in_messages else f"Connection to {hostname} timed out after 5 seconds"
            return False, error_msg
        except ConnectionRefusedError:
            _logger.error(f"Connection refused by {hostname}:{port}")
            error_msg = f"No service is listening on {hostname}:{port}" if include_port_in_messages else f"Host {hostname} is reachable, but no service is listening on any of the ports tested"
            return False, error_msg
        except socket.gaierror as e:
            error_msg = str(e).lower()
            _logger.error(f"DNS resolution failed for {hostname}: {e}")
            
            if 'name or service not known' in error_msg or 'nodename nor servname provided' in error_msg:
                return False, f"Unable to resolve hostname '{hostname}' - please verify the hostname is correct"
            elif 'temporary failure' in error_msg:
                return False, f"Temporary DNS failure for hostname '{hostname}' - please try again later"
            else:
                return False, f"DNS lookup failed for hostname '{hostname}'"
        except OSError as e:
            error_code = getattr(e, 'errno', None)
            error_msg = str(e).lower()
            _logger.error(f"Network error connecting to {hostname}:{port}: {e}")
            
            # Handle specific error codes for better user messages
            
            if error_code == 113 or 'no route to host' in error_msg:
                return False, f"Unable to reach host '{hostname}' - please check your network connectivity"
            elif error_code == 110 or 'connection timed out' in error_msg:
                error_msg = f"Connection to {hostname}:{port} timed out - the host may be unreachable" if include_port_in_messages else f"Connection to {hostname} timed out - host may be unreachable"
                return False, error_msg
            elif 'network is unreachable' in error_msg:
                return False, f"Network is unreachable to '{hostname}' - please check your network configuration"
            elif 'multiple exceptions' in error_msg:
                # Handle IPv6/IPv4 dual stack connection failures
                error_msg = f"Unable to connect to {hostname}:{port} - no service is available" if include_port_in_messages else f"Cannot connect to {hostname} - no service available"
                return False, error_msg
            else:
                error_msg = f"Network error connecting to {hostname}:{port}" if include_port_in_messages else f"Network error connecting to {hostname}"
                return False, error_msg
        except Exception as e:
            _logger.error(f"Unexpected error testing {hostname}:{port}: {e}")
            error_msg = f"Connection test failed for {hostname}:{port}" if include_port_in_messages else f"Connection test failed for {hostname}"
            return False, error_msg
    
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
                    "description": "Host Reachability",
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
                        "description": "Host Reachability",
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
        isHostReachable = False
        failure_reason = None
        
        for hostname in hosts_to_test:
            success, reason = await self.ping_host(hostname)
            if success:
                isHostReachable = True
            else:
                failure_reason = reason
        
        result = {
            "description": "Host Reachability",
            "result": "pass" if isHostReachable else "fail",
            "values": test_values
        }
        
        if not isHostReachable:
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
        is_port_in_config = False # Track if any port is explicitly provided in configuration

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
                    is_port_in_config = True
                break
            
            if not port:
                # Use MQTT defaults if no broker port found
                for default_port in [1883, 8883]:  # MQTT, MQTTS
                    combination_key = f"{hostname}:{default_port}"
                    if combination_key not in processed_combinations:
                        connections_to_test.append((hostname, default_port))
                        processed_combinations.add(combination_key)

                test_values.append({
                    host_item['name']: hostname
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
                        is_port_in_config = True
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
                                is_port_in_config = True
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
                            item['name']: item['value']
                        })

        # Process URLs with ports
        for item in config_items['urls']:
            hostname, port, protocol = self.parse_url(item['value'])
            if hostname and port:
                combination_key = f"{hostname}:{port}"
                is_port_in_config = True
                if combination_key not in processed_combinations:
                    connections_to_test.append((hostname, port))
                    test_values.append({item['name']: item['value']})
                    processed_combinations.add(combination_key)

        # Handle standard address + port combinations (skip if broker processing already handled them)
        if config_items['ports'] and not broker_hosts:
            port_item = config_items['ports'][0]  # Use first port found
            port = port_item['value']
            is_port_in_config = True

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
                    default_ports = [102, 502, 80, 443]  # S7, Modbus, HTTP, HTTPS
                elif 'address' in field_name:
                    # Address fields commonly used for network services
                    default_ports = [502, 80, 443, 44818]  # Modbus, HTTP, HTTPS, EtherNet/IP
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
                    address_item['name']: hostname
                })
                break  # Only process first address to avoid duplicates
        
        if not connections_to_test:
            return None  # No applicable tests
        
        # Test all connections
        isPortConnectivity = False
        failure_reason = None
        
        for hostname, port in connections_to_test:
            success, reason = await self.check_port_listening(hostname, port, include_port_in_messages=is_port_in_config)
            if success:
                isPortConnectivity = True
            else:
                failure_reason = reason
        
        result = {
            "description": "Listening",
            "result": "pass" if isPortConnectivity else "fail",
            "values": test_values
        }
        
        if not isPortConnectivity:
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

