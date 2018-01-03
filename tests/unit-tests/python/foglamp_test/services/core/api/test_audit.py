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

storage_client = StorageClient("0.0.0.0", core_management_port=44645)


# TODO: remove once FOGL-510 is done
@pytest.fixture()
def create_init_data():
    log = '{"end_time": "2017-07-31 13:52:31", "start_time": "2017-07-31 13:52:31", ' \
          '"rows_removed": 0, "rows_remaining": 0, "unsent_rows_removed": 0, "total_failed_to_remove": 0}'
    payload = PayloadBuilder().INSERT(id='1001', code="PURGE", level='2',
                                      log=log, ts='2017-07-31 13:52:31.290372+05:30').payload()
    storage_client.insert_into_tbl("log", payload)

    log = '{"end_time": "2017-07-31 13:53:31", "start_time": "2017-07-31 13:53:31", ' \
          '"rows_removed": 0, "rows_remaining": 0, "unsent_rows_removed": 0, "total_failed_to_remove": 0}'
    payload = PayloadBuilder().INSERT(id='1002', code="PURGE", level='4',
                                      log=log, ts='2017-07-31 13:53:31.300745+05:30').payload()
    storage_client.insert_into_tbl("log", payload)

    log = '{"end_time": "2017-07-31 13:54:31", "start_time": "2017-07-31 13:54:31", ' \
          '"rows_removed": 0, "rows_remaining": 0, "unsent_rows_removed": 0, "total_failed_to_remove": 0}'
    payload = PayloadBuilder().INSERT(id='1003', code="PURGE", level='2',
                                      log=log, ts='2017-07-31 13:54:31.305959+05:30').payload()
    storage_client.insert_into_tbl("log", payload)

    log = '{"end_time": "2017-07-31 13:55:31", "start_time": "2017-07-31 13:55:31", ' \
          '"rows_removed": 0, "rows_remaining": 0, "unsent_rows_removed": 0, "total_failed_to_remove": 0}'
    payload = PayloadBuilder().INSERT(id='1004', code="PURGE", level='2',
                                      log=log, ts='2017-07-31 13:55:31.306996+05:30').payload()
    storage_client.insert_into_tbl("log", payload)

    log = '{"end_time": "2017-07-31 14:05:54", "start_time": "2017-07-31 14:05:54"}'
    payload = PayloadBuilder().INSERT(id='1005', code="LOGGN", level='4',
                                      log=log, ts='2017-07-31 14:05:54.128704+05:30').payload()
    storage_client.insert_into_tbl("log", payload)

    log = '{"end_time": "2017-07-31 14:15:54", "start_time": "2017-07-31 14:15:54", ' \
          '"rows_removed": 0, "rows_remaining": 0, "unsent_rows_removed": 0, "total_failed_to_remove": 0}'
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
    async def test_get_audit(self):
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/audit')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        result = json.loads(r)
        assert 6 == result['totalCount']
        assert 6 == len(result['audit'])

    @pytest.mark.usefixtures('create_init_data')
    async def test_get_audit_with_offset(self):
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/audit?skip=1')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        result = json.loads(r)
        assert 6 == result['totalCount']
        assert 5 == len(result['audit'])

    @pytest.mark.usefixtures('create_init_data')
    async def test_get_audit_by_code(self):
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/audit?source=PURGE')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        result = json.loads(r)
        assert 4 == result['totalCount']
        assert 4 == len(result['audit'])

    @pytest.mark.usefixtures('create_init_data')
    async def test_get_audit_by_code_and_level(self):
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/audit?source=PURGE&severity=ERROR')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        result = json.loads(r)
        assert 3 == result['totalCount']
        assert 3 == len(result['audit'])

    @pytest.mark.usefixtures('create_init_data')
    async def test_get_audit_by_code_and_level_with_limit(self):
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/audit?source=PURGE&severity=ERROR&limit=1')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        result = json.loads(r)
        assert 3 == result['totalCount']
        assert 1 == len(result['audit'])

    @pytest.mark.usefixtures('create_init_data')
    async def test_get_audit_by_code_and_level_with_limit_and_offset(self):
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/audit?source=PURGE&severity=INFORMATION&limit=1&skip=1')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        result = json.loads(r)
        assert 1 == result['totalCount']
        assert 0 == len(result['audit'])

    @pytest.mark.usefixtures('create_init_data')
    async def test_get_audit_with_invalid_severity(self):
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/audit?severity=BLA')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        result = json.loads(r)
        # TODO: FOGL-858
        assert "[KeyError]'BLA'" in result['error']['message']

    @pytest.mark.usefixtures('create_init_data')
    async def test_get_audit_with_invalid_condition(self):
        conn = http.client.HTTPConnection(BASE_URL)
        conn.request("GET", '/foglamp/audit?source=LOGGN&severity=FATAL')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        conn.close()
        result = json.loads(r)
        assert 0 == result['totalCount']
        assert 0 == len(result['audit'])

    # TODO: Also add negative tests for below skip defs
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
