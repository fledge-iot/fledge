# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Tests for iprpc facility """


__author__ = "Deepanshu Yadav"
__copyright__ = "Copyright (c) 2020 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


import os
import json
import http.client
from urllib.parse import quote
import subprocess
import time


def start_south_service_for_filter(config, fledge_url='localhost:8081',
                                   service_name='numpy_ingest', plugin_name='numpy_south', enabled='true'):
    """
        Only starts the south service with configuation provided.
       Args:
           config: The configuation of south service. (json string)
           fledge_url: The url of the fledge api.
           service_name: The name of south service to be executed.
           plugin_name: The name of the installed south plugin.
           enabled : Switch to enable south service
       Returns: Response of addiing south service request in json.
    """
    # Create south service

    data = {"name": service_name, "type": "south", "plugin": plugin_name,
            "enabled": enabled, "config": config}
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("POST", '/fledge/service', json.dumps(data))
    r = conn.getresponse()
    assert 200 == r.status, 'Could not start south service'
    r = r.read().decode()
    conn.close()
    retval = json.loads(r)
    print(retval)


def add_filter(fledge_url, filter_plugin, filter_name, filter_config, plugin_to_filter):
    """
        Adds the filter with configuation provided.
        Args:
            fledge_url: The url of the fledge api.
            filter_plugin: The name of the installed filter plugin.
            filter_name: The name that user wants to give to the filter pipeline.
            filter_config: The configuration of the filter (json string)
            plugin_to_filter: The south service name to which filter is to be applied.
        Returns:
            Response of filter addition request in json
    """
    data = {"name": "{}".format(filter_name), "plugin": "{}".format(filter_plugin), "filter_config": filter_config}
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("POST", '/fledge/filter', json.dumps(data))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert filter_name == jdoc["filter"]

    uri = "{}/pipeline?allow_duplicates=true&append_filter=true".format(quote(plugin_to_filter))
    filters_in_pipeline = [filter_name]
    conn.request("PUT", '/fledge/filter/' + uri, json.dumps({"pipeline": filters_in_pipeline}))
    r = conn.getresponse()
    assert 200 == r.status
    res = r.read().decode()
    jdoc = json.loads(res)
    # Asset newly added filter exist in request's response
    assert filter_name in jdoc["result"]
    return jdoc


def get_service_status(fledge_url):
    """
    Return ping status from fledge.
    Args:
        fledge_url: The URL of Fledge.
    Returns:
        A json string that contains ping status.
    """
    _connection = http.client.HTTPConnection(fledge_url)
    _connection.request("GET", '/fledge/service')
    r = _connection.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return jdoc


def change_category(fledge_url, cat_name, config_item, value):
    """
    Changes the value of configuration item in the given category.
    Args:
        fledge_url: The url of the fledge api.
        cat_name: The category name.
        config_item: The configuration item to be changed.
        value: The new value of configuration item.
    Returns: returns the value of changed category or raises error.
    """
    conn = http.client.HTTPConnection(fledge_url)
    body = {"value": str(value)}
    json_data = json.dumps(body)
    conn.request("PUT", '/fledge/category/{}/{}'.format(cat_name, config_item), json_data)
    r = conn.getresponse()
    # assert 200 == r.status, 'Could not change config item'
    print(r.status)
    r = r.read().decode()
    conn.close()
    retval = json.loads(r)
    print(retval)


def enable_schedule(fledge_url, sch_name):
    """
    Enables schedule.
    Args:
        fledge_url: The url of the fledge api.
        sch_name: The name of schedule to be enabled.
    Returns: Response of enabling schedule in json.
    """
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("PUT", '/fledge/schedule/enable', json.dumps({"schedule_name": sch_name}))
    r = conn.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    assert "scheduleId" in jdoc
    return jdoc


def get_fledge_root():
    """
        Args : None
        Returns: The path which contains FLEDGE_ROOT.
    """
    FLEDGE_ROOT = os.getenv("FLEDGE_ROOT")
    # checking that FLEDGE_ROOT exists
    assert os.path.exists(FLEDGE_ROOT) is True, "The FLEDGE_ROOT does not exist"
    return FLEDGE_ROOT


def install_python_plugin(plugin_path, plugin_type):
    """
        Install the python plugin into Fledge.
        Args:
            plugin_path: The url of the fledge api.
            plugin_type: The name of schedule to be enabled.
        Returns: None
    """
    fledge_root_dir = get_fledge_root()
    dest_dir = os.path.join(fledge_root_dir, 'python', 'fledge', 'plugins', plugin_type)
    subprocess.run(["cp -r {} {}".format(plugin_path, dest_dir)], shell=True, check=True)


def test_reinitialization_of_numpy_without_iprpc(reset_and_start_fledge, fledge_url):
    """
        Test that re initializes numpy inside south plugin as well as inside filter plugin.
        And verifies that the service becomes un responsive as numpy cannot be used inside
        sub interpreters when already used in a parent interpreter.
        Args:
            fledge_url: The url of the fledge api.
            reset_and_start_fledge: A fixture that resets and starts Fledge again.
        Returns: None
    """

    # installing required plugins
    # These are dummy plugins written for reproducing the issue.
    source_directory_for_south_plugin = os.path.join(get_fledge_root(), "tests", "system", "python", "plugins",
                                                     "dummy", "iprpc", "south", "numpy_south")
    source_directory_for_filter_plugin = os.path.join(get_fledge_root(), "tests", "system", "python", "plugins",
                                                      "dummy", "iprpc", "filter", "numpy_filter")
    install_python_plugin(source_directory_for_south_plugin, "south")
    install_python_plugin(source_directory_for_filter_plugin, "filter")

    # Start the south service
    config = {"assetName": {"value": "np_random"},
              "totalValuesArray": {"value": "100"}}
    start_south_service_for_filter(config, service_name="numpy_ingest", plugin_name='numpy_south',
                                   enabled='true')

    # start the filter
    filter_cfg_numpy_filter = {"enable": "true", "assetName": "np_random",
                               "dataPointName": "random", "numSamples": "100"}

    add_filter(fledge_url, "numpy_filter", "numpy_filter_ingest", filter_cfg_numpy_filter, "numpy_ingest")

    # enable schedule
    enable_schedule(fledge_url, "numpy_ingest")

    time.sleep(5)
    cat_name = "numpy_ingest" + "Advanced"
    config_item = "readingsPerSec"
    change_category(fledge_url, cat_name, config_item, "100")

    time.sleep(5)

    # the service will become unresponsive
    status = get_service_status(fledge_url)
    for index, service in enumerate(status['services']):
        if status['services'][index]['name'] == "numpy_ingest":
            service_to_verify = status['services'][index]
            assert service_to_verify['status'] == "unresponsive", "Libraries like numpy cannot be re initialized"


def test_reinitialization_of_numpy_with_iprpc(reset_and_start_fledge, fledge_url):
    """
        Test that uses iprpc facility to use numpy functions inside south plugin as well
        a filter plugin.
        And verifies that the service is up and running with required operations being done.
        Args:
            fledge_url: The url of the fledge api.
            reset_and_start_fledge: A fixture that resets and starts Fledge again.
        Returns: None
    """

    # installing required plugins
    # These are dummy plugins written for reproducing the issue.
    source_directory_for_south_plugin = os.path.join(get_fledge_root(), "tests", "system", "python", "plugins",
                                                     "dummy", "iprpc", "south", "numpy_south")
    source_directory_for_filter_plugin = os.path.join(get_fledge_root(), "tests", "system", "python", "plugins",
                                                      "dummy", "iprpc", "filter", "numpy_iprpc_filter")
    install_python_plugin(source_directory_for_south_plugin, "south")
    install_python_plugin(source_directory_for_filter_plugin, "filter")

    # Start the south service
    config = {"assetName": {"value": "np_random"},
              "totalValuesArray": {"value": "100"}}
    start_south_service_for_filter(config, service_name="numpy_ingest", plugin_name='numpy_south',
                                   enabled='true')

    # start the filter
    filter_cfg_numpy_filter = {"enable": "true", "assetName": "np_random",
                               "dataPointName": "random", "numSamples": "100"}

    add_filter(fledge_url, "numpy_iprpc_filter", "numpy_filter_ingest", filter_cfg_numpy_filter, "numpy_ingest")

    # enable schedule
    enable_schedule(fledge_url, "numpy_ingest")

    time.sleep(5)
    cat_name = "numpy_ingest" + "Advanced"
    config_item = "readingsPerSec"
    change_category(fledge_url, cat_name, config_item, "100")

    time.sleep(5)

    # the service will be running
    status = get_service_status(fledge_url)
    for index, service in enumerate(status['services']):
        if status['services'][index]['name'] == "numpy_ingest":
            service_to_verify = status['services'][index]
            assert service_to_verify['status'] == "running", "Libraries like numpy cannot be re initialized"
