# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test Audit REST API """


import http.client
import json
import time
from collections import Counter
import pytest

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

DEFAULT_AUDIT_COUNT = 14


class TestAudit:

    def test_get_log_codes(self, fledge_url, reset_and_start_fledge):
        expected_code_list = ['PURGE', 'LOGGN', 'STRMN', 'SYPRG', 'START', 'FSTOP',
                              'CONCH', 'CONAD', 'SCHCH', 'SCHAD', 'SRVRG', 'SRVUN',
                              'SRVFL', 'SRVRS', 'NHCOM', 'NHDWN', 'NHAVL', 'UPEXC',
                              'BKEXC', 'NTFDL', 'NTFAD', 'NTFSN', 'NTFCL', 'NTFST',
                              'NTFSD', 'PKGIN', 'PKGUP', 'PKGRM', 'DSPST', 'DSPSD',
                              'ESSRT', 'ESSTP', 'ASTDP', 'ASTUN', 'PIPIN', 'AUMRK',
                              'USRAD', 'USRDL', 'USRCH', 'USRRS']
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/audit/logcode')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert len(expected_code_list) == len(jdoc['logCode'])
        codes = [key['code'] for key in jdoc['logCode']]
        assert Counter(expected_code_list) == Counter(codes)

    def test_get_severity(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/audit/severity')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        log_severity = jdoc['logSeverity']
        assert 4 == len(log_severity)
        name = [name['name'] for name in log_severity]
        assert Counter(['SUCCESS', 'FAILURE', 'WARNING', 'INFORMATION']) == Counter(name)
        index = [idx['index'] for idx in log_severity]
        assert Counter([0, 1, 2, 4]) == Counter(index)

    @pytest.mark.parametrize("request_params, total_count, audit_count", [
        ('', DEFAULT_AUDIT_COUNT, DEFAULT_AUDIT_COUNT),
        ('?limit=1', DEFAULT_AUDIT_COUNT, 1),
        ('?skip=4', DEFAULT_AUDIT_COUNT, 10),
        ('?limit=1&skip=8', DEFAULT_AUDIT_COUNT, 1),
        ('?source=START', 1, 1),
        ('?source=CONAD', 13, 13),
        ('?source=CONAD&limit=1', 13, 1),
        ('?source=CONAD&skip=1', 13, 12),
        ('?source=CONAD&skip=6&limit=1', 13, 1),
        ('?severity=INFORMATION', DEFAULT_AUDIT_COUNT, DEFAULT_AUDIT_COUNT),
        ('?severity=failure', 0, 0),
        ('?source=CONAD&severity=failure', 0, 0),
        ('?source=START&severity=INFORMATION', 1, 1),
        ('?source=START&severity=information&limit=1', 1, 1),
        ('?source=START&severity=information&limit=1&skip=1', 1, 0)
    ])
    def test_default_get_audit(self, fledge_url, wait_time, request_params, total_count, audit_count, storage_plugin):
        # wait for Fledge start, first test only, once in the iteration before start
        if request_params == '':
            time.sleep(wait_time)

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/audit{}'.format(request_params))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        elems = jdoc['audit']
        assert len(jdoc), "No data found"
        assert total_count == jdoc['totalCount']
        assert audit_count == len(elems)

    @pytest.mark.parametrize("payload, total_count", [
        ({"source": "LOGGN", "severity": "warning", "details": {"message": "Engine oil pressure low"}}, 1),
        ({"source": "NHCOM", "severity": "success", "details": {}}, 2),
        ({"source": "START", "severity": "information", "details": {"message": "fledge started"}}, 3),
        ({"source": "CONCH", "severity": "failure", "details": {"message": "Scheduler configuration failed"}}, 4)
    ])
    def test_create_audit_entry(self, fledge_url, payload, total_count):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request('POST', '/fledge/audit', body=json.dumps(payload))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert payload['source'] == jdoc['source']
        assert payload['severity'] == jdoc['severity']
        assert payload['details'] == jdoc['details']

        # Verify new audit log entries
        conn.request("GET", '/fledge/audit')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert DEFAULT_AUDIT_COUNT + total_count == jdoc['totalCount']

    @pytest.mark.parametrize("payload", [
        ({"source": "LOGGN_X", "severity": "warning", "details": {"message": "Engine oil pressure low"}}),
        ({"source": "LOG_X", "severity": "information", "details": {"message": "Engine oil pressure is okay."}})
    ])
    def test_create_nonexistent_log_code_audit_entry(self, fledge_url, payload, storage_plugin):
        if storage_plugin == 'sqlite':
            pytest.skip('TODO: FOGL-2124 Enable foreign key constraint in SQLite')

        msg = "Audit entry cannot be logged."
        conn = http.client.HTTPConnection(fledge_url)
        conn.request('POST', '/fledge/audit', body=json.dumps(payload))
        r = conn.getresponse()
        assert 400 == r.status
        assert msg in r.reason
        r = r.read().decode()
        jdoc = json.loads(r)
        assert msg in jdoc['message']
