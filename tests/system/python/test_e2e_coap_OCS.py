# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test system/python/test_e2e_coap_OCS.py

"""
import os
import subprocess
import http.client
import json
import time
import requests
import pytest

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

TEMPLATE_NAME = "template.json"
SENSOR_VALUE = 20


@pytest.fixture
def prepare_template_reading_from_fogbench():
    def _prepare_template_reading_from_fogbench(FOGBENCH_TEMPLATE, ASSET_NAME):
        """ Define the template file for fogbench readings """
        fogbench_template_path = os.path.join(
            os.path.expandvars('${FOGLAMP_ROOT}'), 'data/{}'.format(FOGBENCH_TEMPLATE))
        f = open(fogbench_template_path, "w")
        f.write(
            '[{"name": "%s", "sensor_values": '
            '[{"name": "sensor", "type": "number", "min": %d, "max": %d, "precision": 0}]}]' % (
                ASSET_NAME, SENSOR_VALUE, SENSOR_VALUE))
        f.close()
        return fogbench_template_path

    return _prepare_template_reading_from_fogbench


@pytest.fixture
def start_south_north(reset_and_start_foglamp, start_south, start_north_ocs_server_c,
                      prepare_template_reading_from_fogbench, remove_data_file,
                      remove_directories, south_branch, foglamp_url,
                      ocs_tenant, ocs_client_id, ocs_client_secret, ocs_namespace, ocs_token,
                      north_plugin="ocs_V2", south_plugin="coap", asset_name="end_to_end_coap"):
    """ This fixture clone a south repo and starts both south and north instance
        reset_and_start_foglamp: Fixture that resets and starts foglamp, no explicit invocation, called at start
        start_south: Fixture that starts any south service with given configuration
        start_north_ocs_server_c: Fixture that starts OCS north task
        remove_data_file: Fixture that remove data file created during the tests
        remove_directories: Fixture that remove directories created during the tests"""

    # fogbench template path for readings
    fogbench_template_path = prepare_template_reading_from_fogbench(TEMPLATE_NAME, asset_name)

    # Call the start south service fixture
    start_south(south_plugin, south_branch, foglamp_url, service_name="coap")

    # Call the start north task fixture
    start_north_ocs_server_c(foglamp_url, north_plugin, ocs_tenant, ocs_client_id, ocs_client_secret,
                             ocs_namespace, ocs_token)

    # Provide the fixture value
    yield start_south_north

    # Cleanup code that runs after the caller test is over
    remove_data_file(fogbench_template_path)
    remove_directories("/tmp/foglamp-south-{}".format(south_plugin))


@pytest.fixture
def start_north_ocs_v2():
    def _start_north_ocs_server_c(foglamp_url, north_plugin, ocs_tenant, ocs_client_id, ocs_client_secret,
                                  ocs_namespace, ocs_token, taskname="North_Readings_to_OCS"):
        """Start north task"""
        conn = http.client.HTTPConnection(foglamp_url)
        data = {"name": taskname,
                "plugin": "{}".format(north_plugin),
                "type": "north",
                "schedule_type": 3,
                "schedule_day": 0,
                "schedule_time": 0,
                "schedule_repeat": 30,
                "schedule_enabled": "true",
                "config": {"tenant_id": {"value": ocs_tenant},
                           "client_id": {"value": ocs_client_id},
                           "client_secret": {"value": ocs_client_secret},
                           "namespace": {"value": ocs_namespace},
                           "producerToken": {"value": ocs_token},
                           }
                }
        conn.request("POST", '/foglamp/scheduled/task', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        retval = r.read().decode()
        return retval

    return _start_north_ocs_server_c
start_north_ocs_server_c = start_north_ocs_v2


@pytest.fixture
def read_data_from_ocs():
    def _read_data_from_ocs(ocs_client_id, ocs_client_secret, ocs_tenant, ocs_namespace, sensor):
        """ This method reads data from OCS web api """
        # TODO: use http.client instead of requests library
        ocs_type_id = 1
        ocs_stream = "{}measurement_{}".format(ocs_type_id, sensor)
        start_timestamp = "2019-01-01T00:00:00.000000Z"
        values_count = 1

        url = 'https://login.windows.net/{0}/oauth2/token'.format(ocs_tenant)

        # Get the access token first
        authorization = requests.post(
            url,
            data={
                'grant_type': 'client_credentials',
                'client_id': ocs_client_id,
                'client_secret': ocs_client_secret,
                'resource': 'https://qihomeprod.onmicrosoft.com/ocsapi'
            }
        )

        # Generate the header using access token
        header = {
            'Authorization': 'bearer %s' % authorization.json()['access_token'],
            'Content-type': 'application/json',
            'Accept': 'text/plain'
        }

        # OCS Cleanup, Delete streams and types if they exist
        streams_url = "https://dat-a.osisoft.com/api/Tenants/{}/Namespaces/{}/{}" \
            .format(ocs_tenant, ocs_namespace, "Streams")
        requests.delete(streams_url, headers=header)
        types_url = "https://dat-a.osisoft.com/api/Tenants/{}/Namespaces/{}/{}" \
            .format(ocs_tenant, ocs_namespace, "Types")
        requests.delete(types_url, headers=header)

        # Get data for stream
        stream_url = "https://dat-a.osisoft.com/api/Tenants/{}/Namespaces/{}/" \
                     "Streams/{}/Data/GetRangeValues?startIndex={}&count={}" \
            .format(ocs_tenant, ocs_namespace, ocs_stream, start_timestamp, values_count)

        response = requests.get(stream_url, headers=header)
        api_output = response.json()
        return api_output

    return _read_data_from_ocs


class TestE2EOCS:
    def test_end_to_end(self, start_south_north, read_data_from_ocs, foglamp_url, wait_time, retries,
                        ocs_client_id, ocs_client_secret, ocs_tenant, ocs_namespace, asset_name="end_to_end_coap"):
        """ Test that data is inserted in FogLAMP and sent to OCS
            start_south_north: Fixture that starts FogLAMP with south and north instance
            read_data_from_ocs: Fixture to read data from OCS
            Assertions:
                on endpoint GET /foglamp/asset
                on endpoint GET /foglamp/asset/<asset_name>
                data received from OCS is same as data sent"""

        conn = http.client.HTTPConnection(foglamp_url)
        time.sleep(wait_time)
        subprocess.run(["cd $FOGLAMP_ROOT/extras/python; python3 -m fogbench -t ../../data/{}; cd -".format(TEMPLATE_NAME)],
                       shell=True, check=True)
        time.sleep(wait_time)
        conn.request("GET", '/foglamp/asset')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        assert len(retval) == 1
        assert asset_name == retval[0]["assetCode"]
        assert 1 == retval[0]["count"]

        conn.request("GET", '/foglamp/asset/{}'.format(asset_name))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        assert {'sensor': SENSOR_VALUE} == retval[0]["reading"]

        retry_count = 0
        data_from_ocs = None
        while (data_from_ocs is None or data_from_ocs == []) and retry_count < retries:
            data_from_ocs = read_data_from_ocs(ocs_client_id, ocs_client_secret, ocs_tenant, ocs_namespace, asset_name)
            retry_count += 1
            time.sleep(wait_time * 2)

        if data_from_ocs is None or retry_count == retries:
            assert False, "Failed to read data from OCS"

        assert data_from_ocs[-1]['sensor'] == SENSOR_VALUE
