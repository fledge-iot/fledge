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


class TestAudit:

    def test_get_log_codes(self, fledge_url, reset_and_start_fledge):
        expected_code_list = ['PURGE', 'LOGGN', 'STRMN', 'SYPRG', 'START', 'FSTOP',
                              'CONCH', 'CONAD', 'SCHCH', 'SCHAD', 'SRVRG', 'SRVUN',
                              'SRVFL', 'NHCOM', 'NHDWN', 'NHAVL', 'UPEXC', 'BKEXC',
                              'NTFDL', 'NTFAD', 'NTFSN', 'NTFCL', 'NTFST', 'NTFSD',
                              'PKGIN', 'PKGUP', 'PKGRM']
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/audit/logcode')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc), "No data found"
        assert 27 == len(jdoc['logCode'])
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
        ('', 11, 11),
        ('?limit=1', 11, 1),
        ('?skip=4', 11, 7),
        ('?limit=1&skip=8', 11, 1),
        ('?source=START', 1, 1),
        ('?source=CONAD', 10, 10),
        ('?source=CONAD&limit=1', 10, 1),
        ('?source=CONAD&skip=1', 10, 9),
        ('?source=CONAD&skip=6&limit=1', 10, 1),
        ('?severity=INFORMATION', 11, 11),
        ('?severity=failure', 0, 0),
        ('?source=CONAD&severity=failure', 0, 0),
        ('?source=START&severity=INFORMATION', 1, 1),
        ('?source=START&severity=information&limit=1', 1, 1),
        ('?source=START&severity=information&limit=1&skip=1', 1, 0)
    ])
    def test_default_get_audit_sqlite(self, fledge_url, wait_time, request_params, total_count, audit_count, storage_plugin):
        if storage_plugin == 'postgres':
            pytest.skip('Test is for SQLite only. Storage category when with SQLite plugin, creates a child category `sqlite` hence one additional CONAD entry.')

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


    @pytest.mark.parametrize("request_params, total_count, audit_count", [
        ('', 10, 10),
        ('?limit=1', 10, 1),
        ('?skip=4', 10, 6),
        ('?limit=1&skip=8', 10, 1),
        ('?source=START', 1, 1),
        ('?source=CONAD', 9, 9),
        ('?source=CONAD&limit=1', 9, 1),
        ('?source=CONAD&skip=1', 9, 8),
        ('?source=CONAD&skip=6&limit=1', 9, 1),
        ('?severity=INFORMATION', 10, 10),
        ('?severity=failure', 0, 0),
        ('?source=CONAD&severity=failure', 0, 0),
        ('?source=START&severity=INFORMATION', 1, 1),
        ('?source=START&severity=information&limit=1', 1, 1),
        ('?source=START&severity=information&limit=1&skip=1', 1, 0)
    ])
    def test_default_get_audit_postgres(self, fledge_url, wait_time, request_params, total_count, audit_count, storage_plugin):
        if storage_plugin == 'sqlite':
            pytest.skip('Test is for PostgreSQL only. Storage category when with SQLite plugin, creates a child category `sqlite` hence one additional CONAD entry.')

        # wait for Fledge start, first test only, once in the iteration before start
        if request_params == '':
            time.sleep(wait_time)

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/audit{}'.format(request_params))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        audit_entries = jdoc['audit']
        assert len(jdoc), "No data found"
        assert total_count == jdoc['totalCount']
        assert audit_count == len(audit_entries)


    @pytest.mark.parametrize("payload, total_count", [
        ({"source": "LOGGN", "severity": "warning", "details": {"message": "Engine oil pressure low"}}, 12),
        ({"source": "NHCOM", "severity": "success", "details": {}}, 13),
        ({"source": "START", "severity": "information", "details": {"message": "fledge started"}}, 14),
        ({"source": "CONCH", "severity": "failure", "details": {"message": "Scheduler configuration failed"}}, 15)
    ])
    def test_create_audit_entry(self, fledge_url, payload, total_count, storage_plugin):
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

        # Storage category when with SQLite plugin, creates a child category `sqlite` hence one additional CONAD entry.
        # CONAD, INFORMATION, '{{"name":"sqlite", ...}'
        # so total_count is being decresed in case of 'postgres' storage engine
        if storage_plugin == 'postgres':
           total_count = total_count -1

        assert len(jdoc), "No data found"
        assert total_count == jdoc['totalCount']

    @pytest.mark.parametrize("payload", [
        ({"source": "LOGGN_X", "severity": "warning", "details": {"message": "Engine oil pressure low"}}),
        ({"source": "LOG_X", "severity": "information", "details": {"message": "Engine oil pressure is okay."}})
    ])
    def test_create_nonexistent_log_code_audit_entry(self, fledge_url, payload, storage_plugin):
        if storage_plugin == 'sqlite':
            pytest.skip('TODO: FOGL-2124 Enable foreign key constraint in SQLite')

        conn = http.client.HTTPConnection(fledge_url)
        conn.request('POST', '/fledge/audit', body=json.dumps(payload))
        r = conn.getresponse()
        assert 400 == r.status
        assert 'Bad Request' in r.reason
        r = r.read().decode()
        jdoc = json.loads(r)
        print(jdoc)
        assert "Audit entry cannot be logged" in jdoc['message']
