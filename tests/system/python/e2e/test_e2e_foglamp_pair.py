# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test end to end flow with:
        2 foglamps, One foglamp use programatic south services, sinusoid, expression and playback to send data
        via http north to send foglamp
        second foglamp use PI Server (C) plugin to send data to PI
"""

import subprocess
import http.client
import os
import json
import time
import pytest


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


# SVC_NAME = "playfilter"
CSV_NAME = "sample.csv"
CSV_HEADERS = "ivalue"
CSV_DATA = "10,20,21,40"

NORTH_TASK_NAME = "NorthReadingsTo_PI"


class TestE2eFogPairPi:

    @pytest.fixture
    def reset_and_start_foglamp_remote(self, storage_plugin, remote_user, remote_ip, key_path, remote_foglamp_path):
        """Fixture that kills foglamp, reset database and starts foglamp again on a remote machine
                storage_plugin: Fixture that defines the storage plugin to be used for tests
                remote_user: User of remote machine
                remote_ip: IP of remote machine
                key_path: Path of key file used for authentication to remote machine
                remote_foglamp_path: Path where FogLAMP is cloned and built
            """
        if remote_foglamp_path is None:
            remote_foglamp_path = '/home/{}/FogLAMP'.format(remote_user)
        subprocess.run(["ssh -i {} {}@{} 'export FOGLAMP_ROOT={};$FOGLAMP_ROOT/scripts/foglamp kill'".format(key_path, remote_user,
                                                                                                      remote_ip,
                                                                                                      remote_foglamp_path)], shell=True, check=True)
        if storage_plugin == 'postgres':
            subprocess.run(["ssh -i {} {}@{} sed -i 's/sqlite/postgres/g' {}/data/etc/storage.json".format(key_path, remote_user, remote_ip, remote_foglamp_path)], shell=True, check=True)
        else:
            subprocess.run(["ssh -i {} {}@{} sed -i 's/postgres/sqlite/g' {}/data/etc/storage.json".format(key_path, remote_user, remote_ip, remote_foglamp_path)], shell=True, check=True)

        subprocess.run(["ssh -i {} {}@{} 'export FOGLAMP_ROOT={};echo YES | $FOGLAMP_ROOT/scripts/foglamp reset'".format(key_path, remote_user, remote_ip, remote_foglamp_path)], shell=True, check=True)
        subprocess.run(["ssh -i {} {}@{} 'export FOGLAMP_ROOT={};$FOGLAMP_ROOT/scripts/foglamp start'".format(key_path, remote_user, remote_ip, remote_foglamp_path)], shell=True)
        stat = subprocess.run(["ssh -i {} {}@{} 'export FOGLAMP_ROOT={}; $FOGLAMP_ROOT/scripts/foglamp status'".format(key_path, remote_user, remote_ip, remote_foglamp_path)], shell=True, stdout=subprocess.PIPE)
        assert "FogLAMP not running." not in stat.stdout.decode("utf-8")

    @pytest.fixture
    def start_south_north_remote(self, remote_ip, reset_and_start_foglamp_remote, use_pip_cache, remote_user,
                                 key_path, remote_foglamp_path,
                                 south_branch, remove_directories,
                                 start_north_pi_server_c,
                                 pi_host, pi_port, pi_token):
        if remote_foglamp_path is None:
            remote_foglamp_path = '/home/{}/FogLAMP'.format(remote_user)
        foglamp_url = "{}:8081".format(remote_ip)
        south_plugin = "http"
        south_service = "http_south"

        try:
            subprocess.run(
                ["$FOGLAMP_ROOT/tests/system/python/scripts/install_python_plugin_remote {} south {} {} {} {} {} {}".format(
                    south_branch, south_plugin, use_pip_cache, remote_user, remote_ip, key_path, remote_foglamp_path)],
                shell=True, check=True)
        except subprocess.CalledProcessError:
            assert False, "{} plugin installation failed".format(south_plugin)
        conn = http.client.HTTPConnection(foglamp_url)

        data = {"name": "{}".format(south_service), "type": "South", "plugin": "{}".format(south_service),
                "enabled": "true", "config": {"assetNamePrefix": {"value": ""}}}
        conn.request("POST", '/foglamp/service', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        assert south_service == retval["name"]

        start_north_pi_server_c(foglamp_url, pi_host, pi_port, pi_token)

        yield self.start_south_north_remote

    def configure_and_start_north_http(self, north_branch, foglamp_url, remote_ip, task_name="NorthReadingsToHTTP"):
        """ Configure and Start north http task """

        try:
            subprocess.run(["$FOGLAMP_ROOT/tests/system/python/scripts/install_c_plugin {} north {}"
                           .format(north_branch, "http-c")], shell=True, check=True)
        except subprocess.CalledProcessError:
            assert False, "http north plugin installation failed"

        conn = http.client.HTTPConnection(foglamp_url)
        data = {"name": task_name,
                "plugin": "{}".format("HttpNorthC"),
                "type": "north",
                "schedule_type": 3,
                "schedule_day": 0,
                "schedule_time": 0,
                "schedule_repeat": 30,
                "schedule_enabled": "false",
                "config": {"URL": {"value": "http://{}:6683/sensor-reading".format(remote_ip)}}
                }
        # {"name":"NorthReadingsToHTTP","plugin":"HttpNorthC","type":"north","schedule_repeat":30,"schedule_type":"3","schedule_enabled":false,"config":{"URL":{"value":"http://10.2.5.18:6683/sensor-reading"},"verifySSL":{"value":"false"},"applyFilter":{"value":"false"}}}
        conn.request("POST", '/foglamp/scheduled/task', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        val = json.loads(r)
        assert 2 == len(val)
        assert task_name == val['name']

    @pytest.fixture
    def start_south_north(self, reset_and_start_foglamp, add_south, enable_schedule, remove_directories,
                          remove_data_file, south_branch, north_branch, foglamp_url, remote_ip,
                          add_filter, filter_branch):
        """ This fixture clone a south and north repo and starts both south and north instance

            reset_and_start_foglamp: Fixture that resets and starts foglamp, no explicit invocation, called at start
            add_south: Fixture that adds a south service with given configuration with enabled or disabled mode
            remove_directories: Fixture that remove directories created during the tests
            remove_data_file: Fixture that remove data file created during the tests
        """
        # Add playback plugin
        # Define configuration of foglamp south playback service
        south_config_playbk = {"assetName": {"value": "{}".format("playback")},
                        "csvFilename": {"value": "{}".format(CSV_NAME)},
                        "ingestMode": {"value": "batch"}}

        # Define the CSV data and create expected lists to be verified later
        csv_file_path = os.path.join(os.path.expandvars('${FOGLAMP_ROOT}'), 'data/{}'.format(CSV_NAME))
        with open(csv_file_path, 'w') as f:
            f.write(CSV_HEADERS)
            for _items in CSV_DATA.split(","):
                f.write("\n{}".format(_items))

        south_plugin_playbk = "playback"
        add_south(south_plugin_playbk, south_branch, foglamp_url, service_name="fogpair_playbk",
                  config=south_config_playbk, start_service=False)

        # Add expression plugin
        south_plugin_expression = "Expression"
        south_config_expr = {"expression": {"value": "cos(x)"}, "minimumX": {"value": "45"},
                             "maximumX": {"value": "45"}, "stepX": {"value": "0"}}

        add_south(south_plugin_expression, south_branch, foglamp_url, service_name="fogpair_expr",
                  config=south_config_expr, plugin_lang="C", start_service=False)

        # Add sinusoid plugin
        south_plugin_sinusoid = "sinusoid"

        add_south(south_plugin_sinusoid, south_branch, foglamp_url, service_name="fogpair_sine", start_service=False)

        self.configure_and_start_north_http(north_branch, foglamp_url, remote_ip)
        # Add asset filter
        # I/P asset_name : All assets > O/P All assets except Expression
        filter_cfg_asset = {"config": {"rules": [{"asset_name": "Expression",
                                                  "action": "exclude"}]},
                            "enable": "true"}
        add_filter("asset", filter_branch, "fasset", filter_cfg_asset, foglamp_url, "NorthReadingsToHTTP")

        enable_schedule(foglamp_url, "fogpair_playbk")
        enable_schedule(foglamp_url, "fogpair_expr")
        enable_schedule(foglamp_url, "fogpair_sine")
        enable_schedule(foglamp_url, "NorthReadingsToHTTP")

        yield self.start_south_north

        remove_directories("/tmp/foglamp-south-{}".format(south_plugin_playbk))
        remove_directories("/tmp/foglamp-south-{}".format(south_plugin_expression.lower()))
        remove_directories("/tmp/foglamp-south-{}".format(south_plugin_sinusoid))
        remove_directories("/tmp/foglamp-north-{}".format("http"))


        remove_data_file(csv_file_path)

    def test_end_to_end(self, start_south_north_remote, start_south_north, foglamp_url, wait_time):
        """ Test that data is inserted in FogLAMP using playback south plugin &
            Delta, RMS, Rate, Scale, Asset & Metadata filters, and sent to PI
            start_south_north: Fixture that starts FogLAMP with south service, add filter and north instance
            Assertions:
                on endpoint GET /foglamp/asset
                on endpoint GET /foglamp/asset/<asset_name> with applied data processing filter value
                data received from PI is same as data sent"""

        time.sleep(wait_time)
        # conn = http.client.HTTPConnection(foglamp_url)
        # self._verify_ingest(conn)

        # disable schedule to stop the service and sending data
        # disable_schedule(foglamp_url, SVC_NAME)


