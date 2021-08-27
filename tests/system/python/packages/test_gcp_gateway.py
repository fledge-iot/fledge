# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test GCP Gateway plugin

"""

import os
import subprocess
import http.client
import json
import time
import pytest
from pathlib import Path
import utils
from datetime import timezone, datetime
import itertools
import platform

__author__ = "Yash Tatkondawar"
__copyright__ = "Copyright (c) 2020 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

task_name = "gcp-gateway"
north_plugin = "GCP"
# This  gives the path of directory where fledge is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPTS_DIR_ROOT = "{}/tests/system/python/packages/data/".format(PROJECT_ROOT)
FLEDGE_ROOT = os.environ.get('FLEDGE_ROOT')
CERTS_DIR = "{}/gcp".format(SCRIPTS_DIR_ROOT)
FLEDGE_CERTS_PEM_DIR = "{}/data/etc/certs/pem/".format(FLEDGE_ROOT)


@pytest.fixture
def check_fledge_root():    
    assert FLEDGE_ROOT, "Please set FLEDGE_ROOT!"


@pytest.fixture
def reset_fledge(wait_time):
    try:
        subprocess.run(["cd {}/tests/system/python/scripts/package && ./reset"
                       .format(PROJECT_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "reset package script failed!"

    # Wait for fledge server to start
    time.sleep(wait_time)


@pytest.fixture
def remove_and_add_pkgs(package_build_version):
    try:
        subprocess.run(["cd {}/tests/system/python/scripts/package && ./remove"
                       .format(PROJECT_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "remove package script failed!"

    try:
        subprocess.run(["cd {}/tests/system/python/scripts/package/ && ./setup {}"
                       .format(PROJECT_ROOT, package_build_version)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "setup package script failed"

    try:
        os_platform = platform.platform()
        pkg_mgr = 'yum' if 'centos' in os_platform or 'redhat' in os_platform else 'apt'
        subprocess.run(["sudo {} install -y fledge-north-gcp fledge-south-sinusoid".format(pkg_mgr)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "installation of gcp-gateway and sinusoid packages failed"

    try:
        subprocess.run(["python3 -m pip install google-cloud-pubsub==1.1.0"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "pip installation of google-cloud-pubsub failed"

    try:
        subprocess.run(["python3 -m pip install google-cloud-logging==1.15.1"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "pip installation of google-cloud-logging failed"

    try:
        subprocess.run(["if [ ! -f \"{}/roots.pem\" ]; then wget https://pki.goog/roots.pem -P {}; fi"
                       .format(CERTS_DIR, CERTS_DIR)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "download of roots.pem failed"


def get_ping_status(fledge_url):
    _connection = http.client.HTTPConnection(fledge_url)
    _connection.request("GET", '/fledge/ping')
    r = _connection.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return jdoc


def get_statistics_map(fledge_url):
    _connection = http.client.HTTPConnection(fledge_url)
    _connection.request("GET", '/fledge/statistics')
    r = _connection.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return utils.serialize_stats_map(jdoc)


# Get the latest 5 timestamps, readings of data sent from south to compare it with the timestamps,
# readings of data in GCP.
def get_asset_info(fledge_url):
    _connection = http.client.HTTPConnection(fledge_url)
    _connection.request("GET", '/fledge/asset/sinusoid?limit=5')
    r = _connection.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    for j in jdoc:
        j['timestamp'] = datetime.strptime(j['timestamp'], "%Y-%m-%d %H:%M:%S.%f").astimezone(
            timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
    return jdoc


def copy_certs(gcp_cert_path):
    # As we are not uploading pem certificate via cert Upload API, therefore below code is required for pem certs
    create_cert_pem_dir = "mkdir -p {}".format(FLEDGE_CERTS_PEM_DIR)
    os.system(create_cert_pem_dir)
    assert os.path.isdir(FLEDGE_CERTS_PEM_DIR)
    copy_file = "cp {} {}/roots.pem {}".format(gcp_cert_path, CERTS_DIR, FLEDGE_CERTS_PEM_DIR)
    os.system(copy_file)
    assert os.path.isfile("{}/roots.pem".format(FLEDGE_CERTS_PEM_DIR))


@pytest.fixture
def verify_and_set_prerequisites(gcp_cert_path, google_app_credentials):
    assert os.path.exists("{}".format(gcp_cert_path)), "Private key not found at {}"\
        .format(gcp_cert_path)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_app_credentials


def verify_received_messages(logger_name, asset_info, retries, wait_time):

    from google.cloud import logging
    from google.cloud.logging import DESCENDING

    # Lists the most recent entries for a given logger.
    logging_client = logging.Client()
    logger = logging_client.logger(logger_name)

    # Fetches the latest logs from GCP and comaperes it with current timestamp
    while retries:
        iterator = logger.list_entries(order_by=DESCENDING, page_size=10, filter_="severity=INFO")
        pages = iterator.pages
        page = next(pages)  # API call
        gcp_log_string = ""
        gcp_info = []
        for entry in page:            
            gcp_log_string += entry.payload
        assert len(gcp_log_string), "No data seen in GCP. "
        gcp_log_dict = json.loads("[" + gcp_log_string.replace("}{", "},{") + "]")
        for r in gcp_log_dict:           
            for d in range(0, len(r["sinusoid"])):
                gcp_info.append(r["sinusoid"][d])
        assert len(gcp_info), "No Sinusoid readings GCP logs found"
        found = 0
        for i in gcp_info:
            for d in asset_info:
                if d['timestamp'] == i['ts']:
                    assert d['reading']['sinusoid'] == i['sinusoid']
                    found += 1
        if found == len(asset_info):
            break
        else:
            retries -= 1
            time.sleep(wait_time)
            
    if retries == 0:
        assert False, "TIMEOUT! sinusoid data sent not seen in GCP. "   


class TestGCPGateway:
    def test_gcp_gateway(self, check_fledge_root, verify_and_set_prerequisites, remove_and_add_pkgs, reset_fledge,
                         fledge_url, wait_time, remove_data_file, gcp_project_id, gcp_device_gateway_id,
                         gcp_registry_id, gcp_cert_path, gcp_logger_name, retries):
        payload = {"name": "Sine", "type": "south", "plugin": "sinusoid", "enabled": True, "config": {}}
        post_url = "/fledge/service"
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", post_url, json.dumps(payload))
        res = conn.getresponse()
        assert 200 == res.status, "ERROR! POST {} request failed".format(post_url)

        copy_certs(gcp_cert_path)

        gcp_project_cfg = {"project_id": {"value": "{}".format(gcp_project_id)},
                           "registry_id": {"value": "{}".format(gcp_registry_id)},
                           "device_id": {"value": "{}".format(gcp_device_gateway_id)},
                           "key": {"value": "rsa_private"}}

        payload = {"name": task_name,
                   "plugin": "{}".format(north_plugin),
                   "type": "north",
                   "schedule_type": 3,
                   "schedule_repeat": 5,
                   "schedule_enabled": True,
                   "config": gcp_project_cfg
                   }

        post_url = "/fledge/scheduled/task"
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("POST", post_url, json.dumps(payload))
        res = conn.getresponse()
        assert 200 == res.status, "ERROR! POST {} request failed".format(post_url)

        time.sleep(wait_time)

        ping_response = get_ping_status(fledge_url)
        assert 0 < ping_response["dataRead"]
        assert 0 < ping_response["dataSent"]

        actual_stats_map = get_statistics_map(fledge_url)
        assert 0 < actual_stats_map['SINUSOID']
        assert 0 < actual_stats_map['READINGS']
        assert 0 < actual_stats_map['Readings Sent']
        assert 0 < actual_stats_map[task_name]

        asset_info = get_asset_info(fledge_url)

        verify_received_messages(gcp_logger_name, asset_info, retries, wait_time)

        remove_data_file("{}/rsa_private.pem".format(FLEDGE_CERTS_PEM_DIR))
        remove_data_file("{}/roots.pem".format(FLEDGE_CERTS_PEM_DIR))
