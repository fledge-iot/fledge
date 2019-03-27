# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test Statistics & Statistics history REST API """


import http.client
import json
import time
from collections import Counter
import pytest

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


KEYS = {'DISCARDED', 'PURGED', 'history_ts', 'READINGS', 'UNSENT', 'UNSNPURGED', 'BUFFERED'}


class TestStatistics:

    def test_default_statistics(self, reset_and_start_foglamp, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/statistics')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 6 == len(jdoc)
        keys = [key['key'] for key in jdoc]
        assert Counter(['BUFFERED', 'DISCARDED', 'PURGED', 'READINGS', 'UNSENT',
                        'UNSNPURGED']) == Counter(keys)

    def test_default_statistics_history(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/statistics/history')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 15 == jdoc['interval']
        assert {} == jdoc['statistics'][0]

    def test_statistics_history_with_stats_collector_schedule(self, foglamp_url, wait_time):
        # wait for sometime for stats collector schedule to start
        time.sleep(wait_time * 3)

        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/statistics/history')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 15 == jdoc['interval']
        assert 1 == len(jdoc['statistics'])
        statistics = jdoc['statistics'][0]
        assert Counter(KEYS) == Counter(statistics.keys())
        del statistics['history_ts']
        assert Counter([0, 0, 0, 0, 0, 0]) == Counter(statistics.values())

    @pytest.mark.parametrize("request_params, keys", [
        ('', KEYS),
        ('?limit=1', KEYS),
        ('?key=READINGS', {'history_ts', 'READINGS'}),
        ('?key=READINGS&limit=1', {'history_ts', 'READINGS'}),
        ('?key=READINGS&limit=0', {}),
    ])
    def test_statistics_history_with_params(self, foglamp_url, request_params, keys):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/statistics/history{}'.format(request_params))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 15 == jdoc['interval']
        assert 1 == len(jdoc['statistics'])
        assert Counter(keys) == Counter(jdoc['statistics'][0].keys())

    @pytest.mark.skip(reason="TODO: will add in future; as a bit tricky one")
    @pytest.mark.parametrize("param", [
        "?minutes=30",
        "?hours=1",
        "?days=1",
        "?minutes=10&hours=1",
        "?hours=1&days=2",
        "?minutes=15&days=1"
    ])
    def test_statistics_history_by_time_based(self, foglamp_url, param):
        pass
