# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import json
import http.client
import pytest
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.storage_client import StorageClient


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Module attributes
BASE_URL = 'localhost:8081'
pytestmark = pytest.mark.asyncio

storage_client = StorageClient("0.0.0.0", core_management_port=43947)


# TODO: remove once FOGL-510 is done
@pytest.fixture()
def create_init_data():
    log = '{"endTime": "2017-07-31 13:52:31", "startTime": "2017-07-31 13:52:31", ' \
          '"rowsRemoved": 0, "rowsRemaining": 0, "unsentRowsRemoved": 0, "totalFailedToRemove": 0}'
    payload = PayloadBuilder().INSERT(id='1001', code="PURGE", level='2',
                                      log=log, ts='2017-07-31 13:52:31.290372+05:30').payload()
    storage_client.insert_into_tbl("log", payload)

    log = '{"endTime": "2017-07-31 13:53:31", "startTime": "2017-07-31 13:53:31", ' \
          '"rowsRemoved": 0, "rowsRemaining": 0, "unsentRowsRemoved": 0, "totalFailedToRemove": 0}'
    payload = PayloadBuilder().INSERT(id='1002', code="PURGE", level='4',
                                      log=log, ts='2017-07-31 13:53:31.300745+05:30').payload()
    storage_client.insert_into_tbl("log", payload)

    log = '{"endTime": "2017-07-31 13:54:31", "startTime": "2017-07-31 13:54:31", ' \
          '"rowsRemoved": 0, "rowsRemaining": 0, "unsentRowsRemoved": 0, "totalFailedToRemove": 0}'
    payload = PayloadBuilder().INSERT(id='1003', code="PURGE", level='2',
                                      log=log, ts='2017-07-31 13:54:31.305959+05:30').payload()
    storage_client.insert_into_tbl("log", payload)

    log = '{"endTime": "2017-07-31 13:55:31", "startTime": "2017-07-31 13:55:31", ' \
          '"rowsRemoved": 0, "rowsRemaining": 0, "unsentRowsRemoved": 0, "totalFailedToRemove": 0}'
    payload = PayloadBuilder().INSERT(id='1004', code="PURGE", level='2',
                                      log=log, ts='2017-07-31 13:55:31.306996+05:30').payload()
    storage_client.insert_into_tbl("log", payload)

    log = '{"endTime": "2017-07-31 14:05:54", "startTime": "2017-07-31 14:05:54"}'
    payload = PayloadBuilder().INSERT(id='1005', code="LOGGN", level='4',
                                      log=log, ts='2017-07-31 14:05:54.128704+05:30').payload()
    storage_client.insert_into_tbl("log", payload)

    log = '{"endTime": "2017-07-31 14:15:54", "startTime": "2017-07-31 14:15:54", ' \
          '"rowsRemoved": 0, "rowsRemaining": 0, "unsentRowsRemoved": 0, "totalFailedToRemove": 0}'
    payload = PayloadBuilder().INSERT(id='1006', code="SYPRG", level='1',
                                      log=log, ts='2017-07-31 14:15:54.131013+05:30').payload()
    storage_client.insert_into_tbl("log", payload)
    yield
    payload = PayloadBuilder().WHERE(["id", ">=", "1001"]).AND_WHERE(["id", "<=", "1006"]).payload()
    storage_client.delete_from_tbl("log", payload)


@pytest.allure.feature("api")
@pytest.allure.story("audit")
class TestAudit:

    async def test_get_severity(self):
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/audit/severity')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        result = json.loads(r)
        log_severity = result['logSeverity']

        # verify the severity count
        assert 4 == len(log_severity)

        # verify the name and value of severity
        for i in range(len(log_severity)):
            if log_severity[i]['index'] == 1:
                assert 1 == log_severity[i]['index']
                assert 'FATAL' == log_severity[i]['name']
            elif log_severity[i]['index'] == 2:
                assert 2 == log_severity[i]['index']
                assert 'ERROR' == log_severity[i]['name']
            elif log_severity[i]['index'] == 3:
                assert 3 == log_severity[i]['index']
                assert 'WARNING' == log_severity[i]['name']
            elif log_severity[i]['index'] == 4:
                assert 4 == log_severity[i]['index']
                assert 'INFORMATION' == log_severity[i]['name']

    async def test_get_log_codes(self):
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/audit/logcode')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        result = json.loads(r)
        log_codes = [key['code'] for key in result['logCode']]

        # verify the default log_codes which are defined in init.sql
        assert 4 == len(log_codes)

        # verify code values
        assert 'PURGE' in log_codes
        assert 'LOGGN' in log_codes
        assert 'STRMN' in log_codes
        assert 'SYPRG' in log_codes

    @pytest.mark.usefixtures('create_init_data')
    @pytest.mark.parametrize("request_params, total_count, audit_count", [
        ('', 6, 6),
        ('?skip=1', 6, 5),
        ('?source=PURGE', 4, 4),
        ('?source=PURGE&severity=error', 3, 3),
        ('?source=PURGE&severity=ERROR&limit=1', 3, 1),
        ('?source=PURGE&severity=INFORMATION&limit=1&skip=1', 1, 0),
        ('?source=LOGGN&severity=FATAL', 0, 0),
        ('?source=&severity=&limit=&skip=', 6, 6)
    ])
    async def test_get_audit_with_params(self, request_params, total_count, audit_count):
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/audit{}'.format(request_params))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        result = json.loads(r)
        assert total_count == result['totalCount']
        assert audit_count == len(result['audit'])

    @pytest.mark.parametrize("request_params, response_code, response_message", [
        ('?limit=invalid', 400, "Limit must be a positive integer"),
        ('?limit=-1', 400, "Limit must be a positive integer"),
        ('?skip=invalid', 400, "Skip/Offset must be a positive integer"),
        ('?skip=-1', 400, "Skip/Offset must be a positive integer"),
        ('?severity=BLA', 400, "'BLA' is not a valid severity"),
        ('?source=blah', 400, "blah is not a valid source")
    ])
    async def test_params_with_bad_data(self, request_params, response_code, response_message):
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/audit{}'.format(request_params))
        r = conn.getresponse()
        conn.close()
        assert response_code == r.status
        assert response_message == r.reason

    # TODO: Also add negative tests for below skipped
    @pytest.mark.skip(reason="FOGL-770 - Not implemented yet (FOGL-769)")
    async def test_post_audit(self):
        pass

    @pytest.mark.skip(reason="FOGL-770 - Not implemented yet (FOGL-769)")
    async def test_get_all_notifications(self):
        pass

    @pytest.mark.skip(reason="FOGL-770 - Not implemented yet (FOGL-769)")
    async def test_get_notification(self):
        pass

    @pytest.mark.skip(reason="FOGL-770 - Not implemented yet (FOGL-769)")
    async def test_post_notification(self):
        pass

    @pytest.mark.skip(reason="FOGL-770 - Not implemented yet (FOGL-769)")
    async def test_update_notification(self):
        pass

    @pytest.mark.skip(reason="FOGL-770 - Not implemented yet (FOGL-769)")
    async def test_delete_notification(self):
        pass
