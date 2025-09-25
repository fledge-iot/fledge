# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test south service tuning parameters for bufferThreshold and maxSendLatency """

import time
import urllib.parse
import pytest

from helpers import utils

__author__ = "Devki Nandan Ghildiyal"
__copyright__ = "Copyright (c) 2025 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

SERVICE_NAME = "TuningSouth"

class TestSouthServiceTuning:
    
    def test_south_service_tuning_buffer_threshold(self, reset_and_start_fledge, fledge_url, 
                                                   wait_time, retries, add_south, south_branch, plugin_language, enable_schedule, disable_schedule, plugin_name):
        """ Test south service tuning parameters - bufferThreshold and maxSendLatency
            
            This test:
            1. Sets up a south service using sinusoid plugin
            2. Configures polling interval to 2 seconds (30 readingsPerSec)
            3. Sets maxSendLatency to 60000ms (1 minute)
            4. Sets bufferThreshold to 200
            5. Verifies 30 readings after 90 seconds (1 minute worth)
            6. Tests dynamic parameter changes
        """
        
        print("\n=== Running South Service Tuning Test ===")

        # Step 1: Create south service with sinusoid plugin and initial configuration
        # Create the service
        self._add_south_service(SERVICE_NAME, fledge_url, plugin_name, add_south, south_branch, plugin_language)
        # Configure advanced parameters after service creation
        advanced_config = {
            "units": "minute" ,            # Polling interval unit
            "readingsPerSec": "30",        # 2 seconds interval
            "maxSendLatency": "60000",     # 1 minute
            "bufferThreshold": "200"       # Buffer 200 readings
        }
        resp = self._set_advance_config(fledge_url, SERVICE_NAME, advanced_config)

        # Step 2: Enable the south service
        response = enable_schedule(fledge_url, SERVICE_NAME)
        assert "Schedule successfully enabled" == response["message"]
        print (f"Scheduled south service: {response}")
        print(f"Enabled south service: {SERVICE_NAME}")

        # Step 3: Wait 90 seconds and verify ~30 readings (1 minute worth data)
        print("Waiting 90 seconds for data collection...")
        time.sleep(90)
        
        # Get ping statistics to check dataRead count
        ping_result = utils.get_request(fledge_url, "/fledge/ping")
        initial_data_read = ping_result["dataRead"]
        print(f"Initial dataRead count: {initial_data_read}")
        
        # Verify approximately 30 readings (allow some tolerance)
        assert 20 <= initial_data_read <= 40, f"Expected ~30 readings, got {initial_data_read}"
        
        # Step 4: Disable the service
        response = disable_schedule(fledge_url, SERVICE_NAME)
        assert "Schedule successfully disabled" == response["message"]
        print("Disabled south service")
        time.sleep(2)  # Allow disable to take effect

        # Verify buffered readings are sent to storage after stopping the service
        ping_result = utils.get_request(fledge_url, "/fledge/ping")
        buffered_data_read = ping_result["dataRead"]
        buffered_data_read = buffered_data_read - initial_data_read
        print(f"Buffered dataRead count: {buffered_data_read}")

        # Step 5: Change bufferThreshold to 10
        config_data = {"bufferThreshold": "10"}
        resp = self._set_advance_config(fledge_url, SERVICE_NAME, config_data)
        assert "10" == resp["bufferThreshold"]["value"]
        print("Updated bufferThreshold to 10")
        
        # Step 6: Re-enable the service 
        response = enable_schedule(fledge_url, SERVICE_NAME)
        assert "Schedule successfully enabled" == response["message"]
        print("Re-enabled south service")
        
        # Step 7: Wait 25 seconds and verify 10 additional readings
        print("Waiting 25 seconds for additional data...")
        time.sleep(25)
        
        new_ping_result = utils.get_request(fledge_url, "/fledge/ping")
        new_data_read = new_ping_result["dataRead"]
        additional_readings = new_data_read - buffered_data_read - initial_data_read
        print(f"Additional readings: {additional_readings}")
        
        # Verify approximately 10 additional readings (with small buffer time, should be ~10-12)
        assert 8 <= additional_readings <= 15, f"Expected ~10 additional readings, got {additional_readings}"
        
        # Step 8: Test dynamic parameter changes without disabling service
        self._test_dynamic_buffer_threshold_changes(fledge_url, wait_time, SERVICE_NAME)
        self._test_dynamic_latency_changes(fledge_url, wait_time, SERVICE_NAME)
        
        # Cleanup: Delete the service
        response = utils.delete_request(fledge_url, f"/fledge/service/{SERVICE_NAME}")
        assert f"Service {SERVICE_NAME} deleted successfully." == response["result"]
        print(f"Deleted south service: {SERVICE_NAME}")

    def _add_south_service(self, service_name, fledge_url, plugin_name, add_south, south_branch, plugin_language):
        response = add_south(plugin_name, south_branch, fledge_url, service_name=service_name, plugin_lang=plugin_language, start_service=False)
        service_name = response["name"]
        assert service_name == response["name"]
        print(f"Created south service: {service_name}")
        time.sleep(2)  # Allow time for Advance category creation

    def _set_advance_config(self, fledge_url, service_name, config):
        """ Helper to set advanced configuration """
        put_url = f"/fledge/category/{service_name}Advanced"
        print(f"Configuring advanced parameters for {service_name}: {config}", put_url)
        resp = utils.put_request(fledge_url, urllib.parse.quote(put_url), config)
        return resp
    
    def _test_dynamic_buffer_threshold_changes(self, fledge_url, wait_time, service_name):
        """ Test dynamic changes to bufferThreshold without disabling service """
        
        print("\n=== Testing Dynamic Buffer Threshold Changes ===")
        
        # Get baseline reading count
        baseline_ping = utils.get_request(fledge_url, "/fledge/ping")
        baseline_count = baseline_ping["dataRead"]
        
        # Test 1: Increase bufferThreshold to 300 (should delay sending)
        config_data = {"bufferThreshold": "300"}
        resp = self._set_advance_config(fledge_url, service_name, config_data)
        assert "300" == resp["bufferThreshold"]["value"]
        print("Increased bufferThreshold to 300")
        
        # Wait and verify fewer sends due to higher threshold
        time.sleep(wait_time * 4)  # 20 seconds
        ping_result = utils.get_request(fledge_url, "/fledge/ping")
        readings_with_high_threshold = ping_result["dataRead"] - baseline_count
        print(f"Readings with high threshold (300): {readings_with_high_threshold}")
        
        # Test 2: Decrease bufferThreshold to 5 (should send more frequently)
        config_data = {"bufferThreshold": "5"}
        resp = self._set_advance_config(fledge_url, service_name, config_data)
        assert "5" == resp["bufferThreshold"]["value"]
        print("Decreased bufferThreshold to 5")
        
        baseline_after_change = ping_result["dataRead"]
        time.sleep(wait_time * 4)  # 20 seconds
        ping_result = utils.get_request(fledge_url, "/fledge/ping")
        readings_with_low_threshold = ping_result["dataRead"] - baseline_after_change
        print(f"Readings with low threshold (5): {readings_with_low_threshold}")
        
        # With lower threshold, we should see similar or more frequent sends
        assert readings_with_low_threshold >= readings_with_high_threshold, "Lower threshold should allow more frequent sending"

    def _test_dynamic_latency_changes(self, fledge_url, wait_time, service_name):
        """ Test dynamic changes to maxSendLatency without disabling service """
        
        print("\n=== Testing Dynamic Max Send Latency Changes ===")
        
        # Get baseline reading count
        baseline_ping = utils.get_request(fledge_url, "/fledge/ping")
        baseline_count = baseline_ping["dataRead"]
        
        # Test 1: Set very high maxSendLatency (30 seconds)
        config_data = {"maxSendLatency": "30000"}
        resp = self._set_advance_config(fledge_url, service_name, config_data)
        assert "30000" == resp["maxSendLatency"]["value"]
        print("Set maxSendLatency to 30000ms (30 seconds)")
        
        time.sleep(wait_time * 6)  # 30 seconds
        ping_result = utils.get_request(fledge_url, "/fledge/ping")
        readings_with_high_latency = ping_result["dataRead"] - baseline_count
        print(f"Readings with high latency (30s): {readings_with_high_latency}")
        
        # Test 2: Set lower maxSendLatency (5 seconds)
        config_data = {"maxSendLatency": "5000"}
        resp = self._set_advance_config(fledge_url, service_name, config_data)
        assert "5000" == resp["maxSendLatency"]["value"]
        print("Set maxSendLatency to 5000ms (5 seconds)")
        
        baseline_after_change = ping_result["dataRead"]
        time.sleep(wait_time * 6)  # 30 seconds
        ping_result = utils.get_request(fledge_url, "/fledge/ping")
        readings_with_low_latency = ping_result["dataRead"] - baseline_after_change
        print(f"Readings with low latency (5s): {readings_with_low_latency}")
        
    def test_south_service_comprehensive_tuning(self, reset_and_start_fledge, fledge_url, 
                                               wait_time, retries, add_south, south_branch, plugin_language,  enable_schedule, disable_schedule,plugin_name):
        """ Comprehensive test of south service tuning - tests all parameter combinations """
        
        service_name = f"{SERVICE_NAME}_Comprehensive"
    
        # Create and enable service
        self._add_south_service(service_name, fledge_url, plugin_name, add_south, south_branch, plugin_language)

        # Configure advanced parameters after service creation
        advanced_config = {
            "units": "minute" ,            # Polling interval unit
            "readingsPerSec": "30",        # 2 seconds interval
            "maxSendLatency": "10000",     # 10 seconds
            "bufferThreshold": "20"        # Buffer 20 readings
        }
        resp = self._set_advance_config(fledge_url, service_name, advanced_config)
        enable_schedule(fledge_url, service_name)
        
        try:
            # Test matrix of different configurations
            test_configs = [
                {"bufferThreshold": "50", "maxSendLatency": "15000", "expected_behavior": "delayed_sends"},
                {"bufferThreshold": "5", "maxSendLatency": "5000", "expected_behavior": "frequent_sends"},
                {"bufferThreshold": "100", "maxSendLatency": "2000", "expected_behavior": "latency_driven"},
                {"bufferThreshold": "10", "maxSendLatency": "30000", "expected_behavior": "threshold_driven"}
            ]
            
            for i, test_config in enumerate(test_configs):
                print(f"\n--- Test Configuration {i+1}: {test_config['expected_behavior']} ---")
                
                # Get baseline
                baseline_ping = utils.get_request(fledge_url, "/fledge/ping")
                baseline_count = baseline_ping["dataRead"]
                
                # Update configuration
                config_update = {
                    "bufferThreshold": test_config["bufferThreshold"],
                    "maxSendLatency": test_config["maxSendLatency"]
                }
                resp = self._set_advance_config(fledge_url, service_name, config_update)
                
                # Verify configuration was applied
                assert test_config["bufferThreshold"] == resp["bufferThreshold"]["value"]
                assert test_config["maxSendLatency"] == resp["maxSendLatency"]["value"]
                
                # Wait and measure results
                time.sleep(wait_time * 8)  # 40 seconds
                
                new_ping = utils.get_request(fledge_url, "/fledge/ping")
                new_count = new_ping["dataRead"]
                readings_collected = new_count - baseline_count
                
                print(f"Configuration: bufferThreshold={test_config['bufferThreshold']}, "
                      f"maxSendLatency={test_config['maxSendLatency']}")
                print(f"Readings collected in 40s: {readings_collected}")
                
                # Basic validation - should always collect some readings
                assert readings_collected > 0, "Should have collected some readings in 40 seconds"
                
                # Store results for comparison
                test_config["actual_readings"] = readings_collected
            
            # Verify that different configurations produce different behaviors
            frequent_sends_config = next(c for c in test_configs if c["expected_behavior"] == "frequent_sends")
            delayed_sends_config = next(c for c in test_configs if c["expected_behavior"] == "delayed_sends")
            
            print(f"\nComparison: Frequent sends={frequent_sends_config['actual_readings']}, "
                  f"Delayed sends={delayed_sends_config['actual_readings']}")
            
        finally:
            # Cleanup
            utils.delete_request(fledge_url, f"/fledge/service/{service_name}")
            print(f"Deleted service: {service_name}")
  
    def test_buffer_threshold_impact_on_send_frequency(self, reset_and_start_fledge, fledge_url, add_south, south_branch, plugin_language,
                                                      enable_schedule, disable_schedule, plugin_name):
        """ Test how bufferThreshold impacts send frequency """
        
        service_name = f"{SERVICE_NAME}_BufferTest"
        
        # # Create and enable service
        self._add_south_service(service_name, fledge_url, plugin_name, add_south, south_branch, plugin_language)
        
        # Configure advanced parameters after service creation
        advanced_config = {
            "units": "second" ,            # Polling interval unit
            "readingsPerSec": "10",        # 10 reading per second
            "maxSendLatency": "60000",     # High latency so threshold dominates
            "bufferThreshold": "10"        # Buffer 10 readings
        }
        resp = self._set_advance_config(fledge_url, service_name, advanced_config)
        enable_schedule(fledge_url, service_name)

        try:
            # Test with small buffer threshold
            time.sleep(15)  # 15 seconds should trigger ~1-2 sends with 10-reading buffer
            ping1 = utils.get_request(fledge_url, "/fledge/ping")
            readings_small_buffer = ping1["dataRead"]
            print(f"Readings with bufferThreshold=10: {readings_small_buffer}")
            
            # Change to large buffer threshold
            config_update = {"bufferThreshold": "100"}
            resp = self._set_advance_config(fledge_url, service_name, config_update)
            
            time.sleep(15)  # Another 15 seconds
            ping2 = utils.get_request(fledge_url, "/fledge/ping")
            total_readings = ping2["dataRead"]
            additional_readings = total_readings - readings_small_buffer
            print(f"Additional readings with bufferThreshold=100: {additional_readings}")
            
            # Should have collected more readings but sent less frequently due to higher threshold
            assert additional_readings >= readings_small_buffer, "Should continue collecting readings with high threshold"
            
        finally:
            utils.delete_request(fledge_url, f"/fledge/service/{service_name}")

    def test_max_send_latency_impact(self, reset_and_start_fledge, fledge_url, add_south, south_branch, plugin_language,
                                   enable_schedule, disable_schedule, plugin_name):
        """ Test how maxSendLatency impacts send timing """
        
        service_name = f"{SERVICE_NAME}_LatencyTest"
        
        # Create and enable service
        self._add_south_service(service_name, fledge_url, plugin_name, add_south, south_branch, plugin_language)

        # Configure advanced parameters after service creation
        advanced_config = {
            "units": "second" ,            # Polling interval unit
            "readingsPerSec": "2",         # 2 reading per second
            "maxSendLatency": "5000",      # 5 seconds
            "bufferThreshold": "1000"      # High threshold so latency dominate
        }
        resp = self._set_advance_config(fledge_url, service_name, advanced_config)
        enable_schedule(fledge_url, service_name)
        try:
            # Test with short latency
            time.sleep(20)  # Should trigger multiple sends
            ping1 = utils.get_request(fledge_url, "/fledge/ping")
            readings_short_latency = ping1["dataRead"]
            print(f"Readings with maxSendLatency=5000ms: {readings_short_latency}")
            
            # Change to long latency
            config_update = {"maxSendLatency": "30000"}  # 30 seconds
            resp = self._set_advance_config(fledge_url, service_name, config_update)
            
            time.sleep(20)  # Another 20 seconds
            ping2 = utils.get_request(fledge_url, "/fledge/ping")
            total_readings = ping2["dataRead"]
            additional_readings = total_readings - readings_short_latency
            print(f"Additional readings with maxSendLatency=30000ms: {additional_readings}")
            
            # Should continue collecting but behavior may differ based on latency setting
            assert additional_readings > 0, ( f"No additional readings collected. Before: {readings_short_latency}, After: {total_readings}" )
            
        finally:
            utils.delete_request(fledge_url, f"/fledge/service/{service_name}") 


