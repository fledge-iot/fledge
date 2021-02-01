# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test end to end flow with:
        2 fledges, One fledge use programatic south services, sinusoid, expression and playback to send data
        via http north to send fledge
        second fledge use PI Server (C) plugin to send data to PI
"""

import subprocess
import http.client
import os
import json
import time
import pytest
from collections import Counter
import utils


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


CSV_NAME = "sample.csv"
CSV_HEADERS = "ivalue"
CSV_DATA = "10,20,21,40"

NORTH_TASK_NAME = "NorthReadingsTo_PI"


class TestE2eFogPairPi:

    def get_asset_list(self, fledge_url):
        _connection = http.client.HTTPConnection(fledge_url)
        _connection.request("GET", '/fledge/asset')
        r = _connection.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        actual_asset_codes = []
        for itm in jdoc:
            actual_asset_codes.append(itm["assetCode"])
        return actual_asset_codes

    def get_ping_status(self, fledge_url):
        _connection = http.client.HTTPConnection(fledge_url)
        _connection.request("GET", '/fledge/ping')
        r = _connection.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        return jdoc

    def get_statistics_map(self, fledge_url):
        _connection = http.client.HTTPConnection(fledge_url)
        _connection.request("GET", '/fledge/statistics')
        r = _connection.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        return utils.serialize_stats_map(jdoc)

    @pytest.fixture
    def reset_and_start_fledge_remote(self, storage_plugin, remote_user, remote_ip, key_path, remote_fledge_path):
        """Fixture that kills fledge, reset database and starts fledge again on a remote machine
                storage_plugin: Fixture that defines the storage plugin to be used for tests
                remote_user: User of remote machine
                remote_ip: IP of remote machine
                key_path: Path of key file used for authentication to remote machine
                remote_fledge_path: Path where Fledge is cloned and built
            """
        if remote_fledge_path is None:
            remote_fledge_path = '/home/{}/fledge'.format(remote_user)
        subprocess.run(["ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i {} {}@{} 'export FLEDGE_ROOT={};$FLEDGE_ROOT/scripts/fledge kill'".format(key_path, remote_user,
                                                                                                      remote_ip,
                                                                                                      remote_fledge_path)], shell=True, check=True)
        if storage_plugin == 'postgres':
            subprocess.run(["ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i {} {}@{} sed -i 's/sqlite/postgres/g' {}/data/etc/storage.json".format(key_path, remote_user, remote_ip, remote_fledge_path)], shell=True, check=True)
        else:
            subprocess.run(["ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i {} {}@{} sed -i 's/postgres/sqlite/g' {}/data/etc/storage.json".format(key_path, remote_user, remote_ip, remote_fledge_path)], shell=True, check=True)

        subprocess.run(["ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i {} {}@{} 'export FLEDGE_ROOT={};echo YES | $FLEDGE_ROOT/scripts/fledge reset'".format(key_path, remote_user, remote_ip, remote_fledge_path)], shell=True, check=True)
        subprocess.run(["ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i {} {}@{} 'export FLEDGE_ROOT={};$FLEDGE_ROOT/scripts/fledge start'".format(key_path, remote_user, remote_ip, remote_fledge_path)], shell=True)
        stat = subprocess.run(["ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i {} {}@{} 'export FLEDGE_ROOT={}; $FLEDGE_ROOT/scripts/fledge status'".format(key_path, remote_user, remote_ip, remote_fledge_path)], shell=True, stdout=subprocess.PIPE)
        assert "Fledge not running." not in stat.stdout.decode("utf-8")

    @pytest.fixture
    def start_south_north_remote(self, reset_and_start_fledge_remote, use_pip_cache, remote_user,
                                 key_path, remote_fledge_path, remote_ip, south_branch,
                                 start_north_pi_server_c, pi_host, pi_port, pi_token):
        """Fixture that starts south and north plugins on remote machine
                reset_and_start_fledge_remote: Fixture that kills fledge, reset database and starts fledge again on a remote machine
                use_pip_cache: flag to tell whether to use python's pip cache for python dependencies
                remote_user: User of remote machine
                remote_fledge_path: Path where Fledge is cloned and built
                remote_ip: IP of remote machine
                south_branch: branch of fledge south plugin
                start_north_pi_server_c: fixture that configures and starts pi plugin
                pi_host: Host IP of PI machine
                pi_token: Token of connector relay of PI
            """

        if remote_fledge_path is None:
            remote_fledge_path = '/home/{}/fledge'.format(remote_user)
        fledge_url = "{}:8081".format(remote_ip)
        south_plugin = "http"
        south_service = "http_south"

        # Install http_south python plugin on remote machine
        try:
            subprocess.run([
                "scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i {} $FLEDGE_ROOT/tests/system/python/scripts/install_python_plugin {}@{}:/tmp/".format(
                    key_path, remote_user, remote_ip)], shell=True, check=True)
            subprocess.run(["ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i {} {}@{} 'export FLEDGE_ROOT={}; /tmp/install_python_plugin {} south {} {}'".format(
                    key_path, remote_user, remote_ip, remote_fledge_path, south_branch, south_plugin, use_pip_cache)],
                shell=True, check=True)

        except subprocess.CalledProcessError:
            assert False, "{} plugin installation failed".format(south_plugin)
        conn = http.client.HTTPConnection(fledge_url)

        # Configure http_south python plugin on remote machine
        data = {"name": "{}".format(south_service), "type": "South", "plugin": "{}".format(south_service),
                "enabled": "true", "config": {"assetNamePrefix": {"value": ""}}}
        conn.request("POST", '/fledge/service', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        assert south_service == retval["name"]

        # Configure pi north plugin on remote machine
        start_north_pi_server_c(fledge_url, pi_host, pi_port, pi_token)

        yield self.start_south_north_remote

    def configure_and_start_north_http(self, north_branch, fledge_url, remote_ip, task_name="NorthReadingsToHTTP"):
        """ Configure and Start north http task """

        try:
            subprocess.run(["$FLEDGE_ROOT/tests/system/python/scripts/install_c_plugin {} north {}"
                           .format(north_branch, "http-c")], shell=True, check=True)
        except subprocess.CalledProcessError:
            assert False, "http north plugin installation failed"

        conn = http.client.HTTPConnection(fledge_url)
        data = {"name": task_name,
                "plugin": "{}".format("httpc"),
                "type": "north",
                "schedule_type": 3,
                "schedule_day": 0,
                "schedule_time": 0,
                "schedule_repeat": 30,
                "schedule_enabled": "false",
                "config": {"URL": {"value": "http://{}:6683/sensor-reading".format(remote_ip)}}
                }

        conn.request("POST", '/fledge/scheduled/task', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        val = json.loads(r)
        assert 2 == len(val)
        assert task_name == val['name']

    @pytest.fixture
    def start_south_north_local(self, reset_and_start_fledge, add_south, enable_schedule, remove_directories,
                                remove_data_file, south_branch, north_branch, fledge_url, remote_ip,
                                add_filter, filter_branch):
        """ This fixture clone a south and north repo and starts both south and north instance

            reset_and_start_fledge: Fixture that resets and starts fledge, no explicit invocation, called at start
            add_south: Fixture that adds a south service with given configuration with enabled or disabled mode
            enable_schedule: Fixture used to enable a schedule
            remove_directories: Fixture that remove directories created during the tests
            remove_data_file: Fixture that remove data file created during the tests
            south_branch: south branch to pull
            north_branch: north branch to pull
            fledge_url: Fledge instance url for local setup (Instance 1)
            remote_ip: IP of remote machine which will receive data from local instance
            add_filter: Fixture that add and configures a filter
            filter_branch: filter branch to pull
        """
        # Add playback plugin
        south_config_playbk = {"assetName": {"value": "{}".format("fogpair_playback")},
                               "csvFilename": {"value": "{}".format(CSV_NAME)},
                               "ingestMode": {"value": "batch"}}

        # Define the CSV data and create expected lists to be verified later
        csv_file_path = os.path.join(os.path.expandvars('${FLEDGE_ROOT}'), 'data/{}'.format(CSV_NAME))
        with open(csv_file_path, 'w') as f:
            f.write(CSV_HEADERS)
            for _items in CSV_DATA.split(","):
                f.write("\n{}".format(_items))

        south_plugin_playbk = "playback"
        add_south(south_plugin_playbk, south_branch, fledge_url, service_name="fogpair_playbk",
                  config=south_config_playbk, start_service=False)

        # Add expression plugin
        south_plugin_expression = "Expression"
        south_config_expr = {"expression": {"value": "cos(x)"}, "minimumX": {"value": "45"},
                             "maximumX": {"value": "45"}, "stepX": {"value": "0"}}

        add_south(south_plugin_expression, south_branch, fledge_url, service_name="fogpair_expr",
                  config=south_config_expr, plugin_lang="C", start_service=False)

        # Add sinusoid plugin
        south_plugin_sinusoid = "sinusoid"

        add_south(south_plugin_sinusoid, south_branch, fledge_url, service_name="fogpair_sine", start_service=False)

        self.configure_and_start_north_http(north_branch, fledge_url, remote_ip)

        # Add asset filter
        # I/P All assets > O/P only fogpair_playback asset
        filter_cfg_asset = {"config": {"rules": [{"asset_name": "fogpair_playback", "action": "include"}],
                                       "defaultAction": "exclude"}, "enable": "true"}
        add_filter("asset", filter_branch, "fasset", filter_cfg_asset, fledge_url, "NorthReadingsToHTTP")

        # Enable all south and north schedules
        enable_schedule(fledge_url, "fogpair_playbk")
        enable_schedule(fledge_url, "fogpair_expr")
        enable_schedule(fledge_url, "fogpair_sine")
        enable_schedule(fledge_url, "NorthReadingsToHTTP")

        yield self.start_south_north_local

        # Cleanup
        remove_directories("/tmp/fledge-south-{}".format(south_plugin_playbk))
        remove_directories("/tmp/fledge-south-{}".format(south_plugin_expression.lower()))
        remove_directories("/tmp/fledge-south-{}".format(south_plugin_sinusoid))
        remove_directories("/tmp/fledge-north-{}".format("http"))
        remove_data_file(csv_file_path)

    def _verify_egress(self, read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                       expected_read_values):
        """
        Verify that data is received in pi db by making calls to PI web api
            read_data_from_pi: Fixture that reads data drom pi
            pi_host: pi host
            pi_admin: pi machine username
            pi_passwd: pi machine password
            pi_db: pi database
            wait_time: wait before making a next call to pi web api
            retries: number of tries to make
            expected_read_values: expected readings value
        """
        retry_count = 0
        data_from_pi = None
        while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
            data_from_pi = read_data_from_pi(pi_host, pi_admin, pi_passwd, pi_db, "fogpair_playback", [CSV_HEADERS])
            retry_count += 1
            time.sleep(wait_time * 2)

        if data_from_pi is None or retry_count == retries:
            assert False, "Failed to read data from PI"

        assert Counter(data_from_pi[CSV_HEADERS][-len(expected_read_values):]) == Counter(expected_read_values)

    def test_end_to_end(self, start_south_north_remote, start_south_north_local,
                        read_data_from_pi, retries, pi_host, pi_admin, pi_passwd, pi_db,
                        fledge_url, remote_ip, wait_time, skip_verify_north_interface):
        """ Test that data is inserted in Fledge (local instance) using playback south plugin,
            sinusoid south plugin and expression south plugin and sent to http north (filter only playback data),
            Fledge (remote instance) receive this data via http south and send to PI
            start_south_north_remote: Fixture that starts Fledge with http south service and pi north instance
            start_south_north_local: Fixture that starts Fledge with south services and north instance with asset filter
            read_data_from_pi: Fixture that reads data from PI web api
            retries: number to retries to make to fetch data from pi
            pi_host: PI host IP
            pi_admin: PI Machine user
            pi_passwd: PI Machine user
            pi_db: PI database
            fledge_url: Local Fledge URL
            remote_ip: IP address where 2 Fledge is running (Remote)
            wait_time: time to wait in sec before making assertions
            skip_verify_north_interface: Flag for assertion of data from Pi web API
            Assertions:
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/asset/<asset_name> with applied data processing filter value
                data received from PI is same as data sent"""

        # Wait for data to be sent to Fledge instance 2 and then to PI
        time.sleep(wait_time * 3)

        # Fledge Instance 1 (Local) verification
        expected_asset_list = ["Expression", "fogpair_playback", "sinusoid"]
        actual_asset_list = self.get_asset_list(fledge_url)
        assert set(expected_asset_list) == set(actual_asset_list)

        ping_response = self.get_ping_status(fledge_url)
        assert 4 <= ping_response["dataRead"]
        assert 4 == ping_response["dataSent"]

        actual_stats_map = self.get_statistics_map(fledge_url)
        assert 1 < actual_stats_map['EXPRESSION']
        assert 1 < actual_stats_map['SINUSOID']
        assert 4 == actual_stats_map['FOGPAIR_PLAYBACK']
        assert 4 == actual_stats_map['NorthReadingsToHTTP']
        assert 6 <= actual_stats_map['READINGS']
        assert 4 == actual_stats_map['Readings Sent']

        # Fledge Instance 2 (Remote) verification
        fledge_url_remote = "{}:8081".format(remote_ip)
        conn_remote = http.client.HTTPConnection(fledge_url_remote)

        expected_list = ["fogpair_playback"]
        actual_asset_list = self.get_asset_list(fledge_url_remote)
        assert set(expected_list) == set(actual_asset_list)

        remote_ping_response = self.get_ping_status(fledge_url_remote)
        assert 4 == remote_ping_response["dataRead"]

        actual_stats_map = self.get_statistics_map(fledge_url_remote)
        assert 'EXPRESSION' not in actual_stats_map.keys()
        assert 'SINUSOID' not in actual_stats_map.keys()
        assert 4 == actual_stats_map['FOGPAIR_PLAYBACK']
        assert 4 == actual_stats_map['READINGS']

        if not skip_verify_north_interface:
            assert 4 == remote_ping_response["dataSent"]
            assert 4 == actual_stats_map['NorthReadingsToPI']
            assert 4 == actual_stats_map['Readings Sent']

        conn_remote.request("GET", '/fledge/asset/{}'.format("fogpair_playback"))
        r = conn_remote.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        tmp_list = CSV_DATA.split(',')
        tmp_list.reverse()
        expected_read_values = [int(x) for x in tmp_list]
        assert len(expected_read_values) == len(jdoc)

        actual_read_values = []
        for itm in jdoc:
            actual_read_values.append(itm['reading'][CSV_HEADERS])
        assert expected_read_values == actual_read_values

        if not skip_verify_north_interface:
            self._verify_egress(read_data_from_pi, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                                expected_read_values)
