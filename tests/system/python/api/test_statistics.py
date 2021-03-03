# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test Statistics & Statistics history REST API """

import os
import subprocess
import http.client
import json
import time
from collections import Counter
import pytest
import utils


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


STATS_KEYS = {'DISCARDED', 'PURGED', 'READINGS', 'UNSENT', 'UNSNPURGED', 'BUFFERED'}
STATS_HISTORY_KEYS = {'history_ts'}
STATS_HISTORY_KEYS.update(STATS_KEYS)
TEMPLATE_NAME = "template.json"
SENSOR_VALUE = 10
PLUGIN_NAME = "coap"
ASSET_NAME = "COAP"


@pytest.fixture
def start_south_coap(add_south, remove_data_file, remove_directories, south_branch,
                     fledge_url, south_plugin=PLUGIN_NAME, asset_name=ASSET_NAME):
    # Define the template file for fogbench
    fogbench_template_path = os.path.join(
        os.path.expandvars('${FLEDGE_ROOT}'), 'data/{}'.format(TEMPLATE_NAME))
    with open(fogbench_template_path, "w") as f:
        f.write(
            '[{"name": "%s", "sensor_values": '
            '[{"name": "sensor", "type": "number", "min": %d, "max": %d, "precision": 0}]}]' % (
                asset_name, SENSOR_VALUE, SENSOR_VALUE))

    add_south(south_plugin, south_branch, fledge_url, service_name=PLUGIN_NAME)

    yield start_south_coap

    # Cleanup code that runs after the caller test is over
    remove_data_file(fogbench_template_path)
    remove_directories("/tmp/fledge-south-{}".format(south_plugin))


class TestStatistics:

    def test_cleanup(self, reset_and_start_fledge):
        # TODO: Remove this workaround
        # Use better setup & teardown methods
        pass

    def test_default_statistics(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/statistics')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert len(STATS_KEYS) == len(jdoc)
        keys = [key['key'] for key in jdoc]
        assert Counter(STATS_KEYS) == Counter(keys)

    def test_default_statistics_history(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/statistics/history')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 15 == jdoc['interval']
        assert {} == jdoc['statistics'][0]

    def test_statistics_history_with_stats_collector_schedule(self, fledge_url, wait_time, retries):
        # wait for sometime for stats collector schedule to start
        time.sleep(wait_time * retries)

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/statistics/history')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 15 == jdoc['interval']
        assert 1 == len(jdoc['statistics'])
        statistics = jdoc['statistics'][0]
        assert Counter(STATS_HISTORY_KEYS) == Counter(statistics.keys())
        del statistics['history_ts']
        assert Counter([0, 0, 0, 0, 0, 0]) == Counter(statistics.values())

    @pytest.mark.parametrize("request_params, keys", [
        ('', STATS_HISTORY_KEYS),
        ('?limit=1', STATS_HISTORY_KEYS),
        ('?key=READINGS', {'history_ts', 'READINGS'}),
        ('?key=READINGS&limit=1', {'history_ts', 'READINGS'}),
        ('?key=READINGS&limit=0', {}),
    ])
    def test_statistics_history_with_params(self, fledge_url, request_params, keys):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/statistics/history{}'.format(request_params))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 15 == jdoc['interval']
        assert 1 == len(jdoc['statistics'])
        assert Counter(keys) == Counter(jdoc['statistics'][0].keys())

    def test_statistics_history_with_service_enabled(self, start_south_coap, fledge_url, wait_time):
        # Allow CoAP listener to start
        time.sleep(wait_time)

        # ingest one reading via fogbench
        subprocess.run(["cd $FLEDGE_ROOT/extras/python; python3 -m fogbench -t ../../data/{}; cd -"
                       .format(TEMPLATE_NAME)], shell=True, check=True)
        # Let the readings to be Ingressed
        time.sleep(wait_time)

        # verify stats
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/statistics')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        stats = utils.serialize_stats_map(jdoc)
        assert 1 == stats[ASSET_NAME.upper()]
        assert 1 == stats['READINGS']

        # Allow stats collector schedule to run i.e. by default 15s
        time.sleep(wait_time * 2 + 1)

        # check stats history
        conn.request("GET", '/fledge/statistics/history')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        stats_history = jdoc['statistics']

        # READINGS & ASSET_NAME keys and verify no duplicate entry found with value 1
        read = [r['READINGS'] for r in stats_history]
        assert 1 in read
        assert 1 == read.count(1)
        # print(stats_history)
        asset_stats_history = [a for a in stats_history if ASSET_NAME.upper() in a.keys()]
        assert any(ash[ASSET_NAME.upper()] == 1 for ash in asset_stats_history), "Failed to find statistics history " \
                                                                                 "record for " + ASSET_NAME.upper()

        # verify stats history by READINGS key only
        conn.request("GET", '/fledge/statistics/history?key={}'.format('READINGS'))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        read = [r['READINGS'] for r in jdoc['statistics']]
        assert 1 in read
        assert 1 == read.count(1)

        # verify stats history by ASSET_NAME key only
        conn.request("GET", '/fledge/statistics/history?key={}'.format(ASSET_NAME.upper()))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        asset = [a[ASSET_NAME.upper()] for a in jdoc['statistics']]
        assert 1 in asset
        assert 1 == asset.count(1)
