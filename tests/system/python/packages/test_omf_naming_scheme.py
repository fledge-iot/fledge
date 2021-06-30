# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test OMF North Service System tests:
        Tests OMF as a north service along with reconfiguration.
"""

__author__ = "Yash Tatkondawar"
__copyright__ = "Copyright (c) 2021 Dianomic Systems, Inc."

import subprocess
import time
from pathlib import Path
import pytest
import utils
import os

south_plugin = "coap"
south_asset_name = "coap"
south_service_name = "CoAP #1"
north_plugin = "OMF"
north_task_name = "NorthReadingsToPI_WebAPI"
TEMPLATE_NAME = "template.json"
DATAPOINT = "sensor"
DATAPOINT_VALUE = 20
# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPTS_DIR_ROOT = "{}/tests/system/python/scripts/package/".format(PROJECT_ROOT)


@pytest.fixture
def reset_fledge(wait_time):
    try:
        subprocess.run(["cd {} && ./reset"
                       .format(SCRIPTS_DIR_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "reset package script failed!"


@pytest.fixture
def start_south(add_south, remove_data_file, fledge_url):
    """ This fixture
        clean_setup_fledge_packages: purge the fledge* packages and install latest for given repo url
        add_south: Fixture that adds a south service with given configuration
        start_north_task_omf_web_api: Fixture that starts PI north task
        remove_data_file: Fixture that remove data file created during the tests """

    # Define the template file for fogbench
    fogbench_template_path = os.path.join(
        os.path.expandvars('{}'.format(PROJECT_ROOT)), 'data/{}'.format(TEMPLATE_NAME))
    with open(fogbench_template_path, "w") as f:
        f.write(
            '[{"name": "%s", "sensor_values": '
            '[{"name": "%s", "type": "number", "min": %d, "max": %d, "precision": 0}]}]' % (
                south_asset_name, DATAPOINT, DATAPOINT_VALUE, DATAPOINT_VALUE))

    add_south(south_plugin, None, fledge_url, service_name="{}".format(south_service_name), installation_type='package')

    yield start_south

    # Cleanup code that runs after the caller test is over
    remove_data_file(fogbench_template_path)


def verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries):
    get_url = "/fledge/ping"
    ping_result = utils.get_request(fledge_url, get_url)
    assert "dataRead" in ping_result
    assert "dataSent" in ping_result
    assert 0 < ping_result['dataRead'], "South data NOT seen in ping header"

    retry_count = 1
    sent = 0
    if not skip_verify_north_interface:
        while retries > retry_count:
            sent = ping_result["dataSent"]
            if sent >= 1:
                break
            else:
                time.sleep(wait_time)

            retry_count += 1
            ping_result = utils.get_request(fledge_url, get_url)

        assert 1 <= sent, "Failed to send data via PI Web API using Basic auth"
    return ping_result


def verify_statistics_map(fledge_url, skip_verify_north_interface):
    get_url = "/fledge/statistics"
    jdoc = utils.get_request(fledge_url, get_url)
    actual_stats_map = utils.serialize_stats_map(jdoc)
    assert 1 <= actual_stats_map[south_asset_name.upper()]
    assert 1 <= actual_stats_map['READINGS']
    if not skip_verify_north_interface:
        assert 1 <= actual_stats_map['Readings Sent']
        assert 1 <= actual_stats_map[north_task_name]


def verify_service_added(fledge_url):
    get_url = "/fledge/south"
    result = utils.get_request(fledge_url, get_url)
    assert len(result["services"])
    assert south_service_name in [s["name"] for s in result["services"]]

    get_url = "/fledge/service"
    result = utils.get_request(fledge_url, get_url)
    assert len(result["services"])
    assert south_service_name in [s["name"] for s in result["services"]]


def verify_asset(fledge_url):
    get_url = "/fledge/asset"
    result = utils.get_request(fledge_url, get_url)
    assert len(result), "No asset found"
    assert south_asset_name in [s["assetCode"] for s in result]


def verify_asset_tracking_details(fledge_url, skip_verify_north_interface):
    tracking_details = utils.get_asset_tracking_details(fledge_url, "Ingest")
    assert len(tracking_details["track"]), "Failed to track Ingest event"
    tracked_item = tracking_details["track"][0]
    assert south_service_name == tracked_item["service"]
    assert south_asset_name == tracked_item["asset"]
    assert south_asset_name == tracked_item["plugin"]

    if not skip_verify_north_interface:
        egress_tracking_details = utils.get_asset_tracking_details(fledge_url, "Egress")
        assert len(egress_tracking_details["track"]), "Failed to track Egress event"
        tracked_item = egress_tracking_details["track"][0]
        assert north_task_name == tracked_item["service"]
        assert south_asset_name == tracked_item["asset"]
        assert north_plugin == tracked_item["plugin"]


def _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                   recorded_datapoint, pi_asset_name):
    retry_count = 0
    data_from_pi = None

    af_hierarchy_level = "fledge/room1/machine1"
    af_hierarchy_level_list = af_hierarchy_level.split("/")

    while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
        data_from_pi = read_data_from_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, af_hierarchy_level_list,
                                                 pi_asset_name, {recorded_datapoint})
        retry_count += 1
        time.sleep(wait_time * 2)

    if data_from_pi is None or retry_count == retries:
        assert False, "Failed to read data from PI"

    assert data_from_pi[recorded_datapoint][-1] == DATAPOINT_VALUE


class TestOMFNamingScheme:
    def test_omf_with_concise_naming(self, clean_setup_fledge_packages, reset_fledge, start_south,
                                     start_north_task_omf_web_api,
                                     read_data_from_pi_web_api, skip_verify_north_interface, fledge_url,
                                     wait_time, retries, pi_host, pi_port, pi_admin, pi_passwd, pi_db):
        """ Test OMF with concise naming scheme.
            clean_setup_fledge_packages: Fixture to remove and install latest fledge packages
            reset_fledge: Fixture to reset fledge
            start_south: Adds and configures south service
            start_north_task_omf_web_api: Adds and configures north service
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        start_north_task_omf_web_api(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd,
                                        naming_scheme="Concise")
        subprocess.run(
            ["cd {}/extras/python; python3 -m fogbench -t ../../data/{}; cd -".format(PROJECT_ROOT, TEMPLATE_NAME)],
            shell=True, check=True)

        # Wait until south and north services/tasks are created and some data is loaded
        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, verify_asset_tracking_details)

        if not skip_verify_north_interface:
            recorded_datapoint = "{}".format(south_asset_name)
            # Name of asset in the PI server
            pi_asset_name = "{}".format(south_asset_name)
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           recorded_datapoint, pi_asset_name)

    def test_omf_with_type_suffix_naming(self, reset_fledge, start_south, start_north_task_omf_web_api,
                                         read_data_from_pi_web_api, skip_verify_north_interface, fledge_url,
                                         wait_time, retries, pi_host, pi_port, pi_admin, pi_passwd, pi_db):
        """ Test OMF with concise naming scheme.
            clean_setup_fledge_packages: Fixture to remove and install latest fledge packages
            reset_fledge: Fixture to reset fledge
            start_south: Adds and configures south service
            start_north_task_omf_web_api: Adds and configures north service
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        start_north_task_omf_web_api(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd,
                                        naming_scheme="Use Type Suffix")
        subprocess.run(
            ["cd {}/extras/python; python3 -m fogbench -t ../../data/{}; cd -".format(PROJECT_ROOT, TEMPLATE_NAME)],
            shell=True, check=True)

        # Wait until south and north services/tasks are created and some data is loaded
        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, verify_asset_tracking_details)

        if not skip_verify_north_interface:
            type_id = 1
            recorded_datapoint = "{}".format(south_asset_name)
            # Name of asset in the PI server
            pi_asset_name = "{}-type{}".format(south_asset_name, type_id)
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           recorded_datapoint, pi_asset_name)

    def test_omf_with_attribute_hash_naming(self, reset_fledge, start_south, start_north_task_omf_web_api,
                                            read_data_from_pi_web_api, skip_verify_north_interface, fledge_url,
                                            wait_time, retries, pi_host, pi_port, pi_admin, pi_passwd, pi_db):
        """ Test OMF with concise naming scheme.
            clean_setup_fledge_packages: Fixture to remove and install latest fledge packages
            reset_fledge: Fixture to reset fledge
            start_south: Adds and configures south service
            start_north_task_omf_web_api: Adds and configures north service
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        start_north_task_omf_web_api(fledge_url, pi_host, pi_port, pi_user=pi_admin, pi_pwd=pi_passwd,
                                        naming_scheme="Use Attribute Hash")
        subprocess.run(
            ["cd {}/extras/python; python3 -m fogbench -t ../../data/{}; cd -".format(PROJECT_ROOT, TEMPLATE_NAME)],
            shell=True, check=True)

        # Wait until south and north services/tasks are created and some data is loaded
        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, verify_asset_tracking_details)

        if not skip_verify_north_interface:
            type_id = 1
            recorded_datapoint = "{}measurement_{}".format(type_id, south_asset_name)
            # Name of asset in the PI server
            pi_asset_name = "{}".format(south_asset_name)
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           recorded_datapoint, pi_asset_name)

    def test_omf_with_backward_compatibility_naming(self, reset_fledge, start_south, start_north_task_omf_web_api,
                                                    read_data_from_pi_web_api, skip_verify_north_interface, fledge_url,
                                                    wait_time, retries, pi_host, pi_port, pi_admin, pi_passwd, pi_db):
        """ Test OMF with concise naming scheme.
            clean_setup_fledge_packages: Fixture to remove and install latest fledge packages
            reset_fledge: Fixture to reset fledge
            start_south: Adds and configures south service
            start_north_task_omf_web_api: Adds and configures north service
            read_data_from_pi_web_api: Fixture to read data from PI web API
            skip_verify_north_interface: Flag for assertion of data using PI web API
            Assertions:
                on endpoint GET /fledge/ping
                on endpoint GET /fledge/south
                on endpoint GET /fledge/north
                on endpoint GET /fledge/service
                on endpoint GET /fledge/statistics
                on endpoint GET /fledge/asset
                on endpoint GET /fledge/track"""

        start_north_task_omf_web_api(fledge_url, pi_host, pi_port, pi_user=pi_admin,
                                        pi_pwd=pi_passwd)
        subprocess.run(
            ["cd {}/extras/python; python3 -m fogbench -t ../../data/{}; cd -".format(PROJECT_ROOT, TEMPLATE_NAME)],
            shell=True, check=True)

        # Wait until south and north services/tasks are created and some data is loaded
        time.sleep(wait_time)

        verify_ping(fledge_url, skip_verify_north_interface, wait_time, retries)
        verify_asset(fledge_url)
        verify_service_added(fledge_url)
        verify_statistics_map(fledge_url, skip_verify_north_interface)
        verify_asset_tracking_details(fledge_url, verify_asset_tracking_details)

        if not skip_verify_north_interface:
            type_id = 1
            recorded_datapoint = "{}measurement_{}".format(type_id, south_asset_name)
            # Name of asset in the PI server
            pi_asset_name = "{}-type{}".format(south_asset_name, type_id)
            _verify_egress(read_data_from_pi_web_api, pi_host, pi_admin, pi_passwd, pi_db, wait_time, retries,
                           recorded_datapoint, pi_asset_name)
