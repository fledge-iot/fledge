# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

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
from datetime import datetime

__author__ = "Yash Tatkondawar"
__copyright__ = "Copyright (c) 2020 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

task_name = "gcp-gateway"
north_plugin = "GCP"
# This  gives the path of directory where FogLAMP is cloned. test_file < packages < python < system < tests < ROOT
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPTS_DIR_ROOT = "{}/tests/system/python/packages/data/".format(PROJECT_ROOT)
FOGLAMP_ROOT = os.environ.get('FOGLAMP_ROOT')
CERTS_DIR = "{}/gcp".format(SCRIPTS_DIR_ROOT)
FOGLAMP_CERTS_DIR = "{}/data/etc/certs/".format(FOGLAMP_ROOT)


@pytest.fixture
def reset_foglamp(wait_time):
    try:
        subprocess.run(["cd {}/tests/system/python/scripts/package && ./reset"
                       .format(PROJECT_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "reset package script failed!"

    # Wait for foglamp server to start
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
        subprocess.run(["sudo apt install -y foglamp-north-gcp foglamp-south-sinusoid"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "installation of gcp-gateway and sinusoid packages failed"

    try:
        subprocess.run(["python3 -m pip install google-cloud-pubsub==1.1.0"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "pip installation of google-cloud-pubsub failed"

    try:
        subprocess.run(["if [ ! -f \"{}/roots.pem\" ]; then wget https://pki.goog/roots.pem -P {}; fi"
                       .format(CERTS_DIR, CERTS_DIR)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "download of roots.pem failed"


def get_ping_status(foglamp_url):
    _connection = http.client.HTTPConnection(foglamp_url)
    _connection.request("GET", '/foglamp/ping')
    r = _connection.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return jdoc


def get_statistics_map(foglamp_url):
    _connection = http.client.HTTPConnection(foglamp_url)
    _connection.request("GET", '/foglamp/statistics')
    r = _connection.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return utils.serialize_stats_map(jdoc)


def copy_certs(gcp_cert_path):
    copy_file = "cp {} {}/roots.pem {}".format(gcp_cert_path, CERTS_DIR, FOGLAMP_CERTS_DIR)
    exit_code = os.system(copy_file)
    assert 0 == exit_code


@pytest.fixture
def verify_and_set_prerequisites(gcp_cert_path, google_app_credentials):
    assert os.path.exists("{}".format(gcp_cert_path)), "Private key not found at {}"\
        .format(gcp_cert_path)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_app_credentials


def verify_received_messages(project_id, subscription_name, timeout=None):
    """Receives messages from a pull subscription."""
    # [START pubsub_subscriber_async_pull]
    # [START pubsub_quickstart_subscriber]
    from google.cloud import pubsub_v1

    # TODO project_id = "Your Google Cloud Project ID"
    # TODO subscription_name = "Your Pub/Sub subscription name"
    # TODO timeout = 5.0  # "How long the subscriber should listen for
    # messages in seconds"

    subscriber = pubsub_v1.SubscriberClient()
    # The `subscription_path` method creates a fully qualified identifier
    # in the form `projects/{project_id}/subscriptions/{subscription_name}`
    subscription_path = subscriber.subscription_path(
        project_id, subscription_name
    )

    def callback(message):
        msg_json = json.loads(message.data.decode('utf8'))
        ts = msg_json["sinusoid"][0]["ts"]
        # received messages may not be in order (and latest). verify date part only
        # until we found a way to fetch latest sent and stats count from GCP
        assert ts[:10] == datetime.now().strftime("%Y-%m-%d")
        message.ack()

    streaming_pull_future = subscriber.subscribe(
        subscription_path, callback=callback
    )

    # result() in a future will block indefinitely if `timeout` is not set,
    # unless an exception is encountered first.
    try:
        streaming_pull_future.result(timeout=timeout)
    except:  # noqa
        streaming_pull_future.cancel()
    # [END pubsub_subscriber_async_pull]
    # [END pubsub_quickstart_subscriber]


class TestGCPGateway:
    def test_gcp_gateway(self, verify_and_set_prerequisites, remove_and_add_pkgs, reset_foglamp, foglamp_url,
                         wait_time, remove_data_file, gcp_project_id, gcp_device_gateway_id, gcp_registry_id,
                         gcp_subscription_name, gcp_cert_path):
        payload = {"name": "Sine", "type": "south", "plugin": "sinusoid", "enabled": True, "config": {}}
        post_url = "/foglamp/service"
        conn = http.client.HTTPConnection(foglamp_url)
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

        post_url = "/foglamp/scheduled/task"
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("POST", post_url, json.dumps(payload))
        res = conn.getresponse()
        assert 200 == res.status, "ERROR! POST {} request failed".format(post_url)

        time.sleep(wait_time)

        ping_response = get_ping_status(foglamp_url)
        assert 0 < ping_response["dataRead"]
        assert 0 < ping_response["dataSent"]

        actual_stats_map = get_statistics_map(foglamp_url)
        assert 0 < actual_stats_map['SINUSOID']
        assert 0 < actual_stats_map['READINGS']
        assert 0 < actual_stats_map['Readings Sent']
        assert 0 < actual_stats_map[task_name]

        verify_received_messages(gcp_project_id, gcp_subscription_name, timeout=3)

        remove_data_file("{}/rsa_private.pem".format(FOGLAMP_CERTS_DIR))
        remove_data_file("{}/roots.pem".format(FOGLAMP_CERTS_DIR))
