# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge.readthedocs.io/
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


class TestAudit:

    def test_get_log_codes(self, fledge_url, reset_and_start_fledge):
        expected_code_list = ['PURGE', 'LOGGN', 'STRMN', 'SYPRG', 'START', 'FSTOP',
                              'CONCH', 'CONAD', 'SCHCH', 'SCHAD', 'SRVRG', 'SRVUN',
                              'SRVFL', 'NHCOM', 'NHDWN', 'NHAVL', 'UPEXC', 'BKEXC',
                              'NTFDL', 'NTFAD', 'NTFSN', 'NTFCL', 'NTFST', 'NTFSD',
                              'PKGIN', 'PKGUP']
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/audit/logcode')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 26 == len(jdoc['logCode'])
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

    @pytest.mark.parametrize("request_params, total_count, audit_count, cat_name", [
        ('', 9, 9, ''),
        ('?limit=1', 9, 1, ''),
        ('?skip=4', 9, 5, 'Installation'),
        ('?limit=1&skip=8', 9, 1, 'SCHEDULER'),
        ('?source=START', 1, 1, ''),
        ('?source=CONAD', 8, 8, 'Utilities'),
        ('?source=CONAD&limit=1', 8, 1, 'Utilities'),
        ('?source=CONAD&skip=1', 8, 7, 'Advanced'),
        ('?source=CONAD&skip=6&limit=1', 8, 1, 'SMNTR'),
        ('?severity=INFORMATION', 9, 9, ''),
        ('?severity=failure', 0, 0, ''),
        ('?source=CONAD&severity=failure', 0, 0, ''),
        ('?source=START&severity=INFORMATION', 1, 1, ''),
        ('?source=START&severity=information&limit=1', 1, 1, ''),
        ('?source=START&severity=information&limit=1&skip=1', 1, 0, '')
    ])
    def test_default_get_audit(self, fledge_url, wait_time, request_params, total_count, audit_count, cat_name):
        if request_params == '':
            time.sleep(wait_time)
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/audit{}'.format(request_params))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert total_count == jdoc['totalCount']
        assert audit_count == len(jdoc['audit'])
        if audit_count:
            if jdoc['audit'][0]['details']:
                assert cat_name == jdoc['audit'][0]['details']['name']

    @pytest.mark.parametrize("payload, total_count", [
        ({"source": "LMTR", "severity": "warning", "details": {"message": "Engine oil pressure low"}}, 10),
        ({"source": "LMTR", "severity": "success", "details": {}}, 11),
        ({"source": "START", "severity": "information", "details": {"message": "fledge started"}}, 12),
        ({"source": "CONCH", "severity": "failure", "details": {"message": "Scheduler configuration failed"}}, 13)
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
        assert total_count == jdoc['totalCount']
