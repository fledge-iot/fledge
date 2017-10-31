# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import pytest
import os
import py
import json
from foglamp.storage.payload_builder import PayloadBuilder
from foglamp.storage.storage import Storage

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

store = Storage("0.0.0.0", core_management_port=37251)

# TODO: remove once FOGL-510 is done
@pytest.fixture(scope="module", autouse=True)
def create_init_data():
    """
    Module level fixture that is called once for the test
        Before the tests starts, it creates the init data
        After all the tests, it clears database and sets the init data
    Fixture called by default (autouse=True)
    """
    _dir = os.path.dirname(os.path.realpath(__file__))
    file_path = py.path.local(_dir).join('/foglamp_test_storage_init.sql')
    os.system("psql < {} > /dev/null 2>&1".format(file_path))
    yield
    os.system("psql < `locate foglamp_ddl.sql | grep 'FogLAMP/src/sql'` > /dev/null 2>&1")
    os.system("psql < `locate foglamp_init_data.sql | grep 'FogLAMP/src/sql'` > /dev/null 2>&1")


@pytest.allure.feature("api")
@pytest.allure.story("storage client")
class TestStorageRead:
    """This class tests SELECT (Read) queries of Storage layer using payload builder
    """
    def test_select(self):
        payload = PayloadBuilder().SELECT().payload()
        result = store.query_tbl_with_payload("statistics", payload)
        assert len(result["rows"]) == 2
        assert result["count"] == 2
        assert result["rows"][0]["key"] == "TEST_1"
        assert result["rows"][0]["description"] == "Testing the storage service data 1"
        assert result["rows"][0]["value"] == 10
        assert result["rows"][0]["previous_value"] == 2

        assert result["rows"][1]["key"] == "TEST_2"
        assert result["rows"][1]["description"] == "Testing the storage service data 2"
        assert result["rows"][1]["value"] == 15
        assert result["rows"][1]["previous_value"] == 2

    def test_where_query_param(self):
        payload = PayloadBuilder().WHERE(["key", "=", "TEST_1"]).query_params()
        result = store.query_tbl("statistics", payload)
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["key"] == "TEST_1"
        assert result["rows"][0]["description"] == "Testing the storage service data 1"
        assert result["rows"][0]["value"] == 10
        assert result["rows"][0]["previous_value"] == 2

    def test_where_payload(self):
        payload = PayloadBuilder().WHERE(["value", "!=", 15]).payload()
        result = store.query_tbl_with_payload("statistics", payload)
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["key"] == "TEST_1"
        assert result["rows"][0]["description"] == "Testing the storage service data 1"
        assert result["rows"][0]["value"] == 10
        assert result["rows"][0]["previous_value"] == 2

    def test_where_invalid_key(self):
        payload = PayloadBuilder().WHERE(["bla", "=", "invalid"]).payload()
        result = store.query_tbl_with_payload("statistics", payload)
        assert "ERROR" in result["message"]

    def test_multiple_and_where(self):
        payload = PayloadBuilder().WHERE(["asset_code", "=", 'TEST_STORAGE_CLIENT']).\
            AND_WHERE(["read_key", "!=", '57179e0c-1b53-47b9-94f3-475cdba60628']). \
            AND_WHERE(["read_key", "=", '7016622d-a4db-4ec0-8b97-85f6057317f1']).payload()
        result = store.query_tbl_with_payload("readings", payload)
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["read_key"] == "7016622d-a4db-4ec0-8b97-85f6057317f1"
        assert result["rows"][0]["asset_code"] == "TEST_STORAGE_CLIENT"
        assert result["rows"][0]["reading"] == json.loads('{"sensor_code_1": 80, "sensor_code_2": 5.8}')

    def test_multiple_or_where(self):
        payload = PayloadBuilder().WHERE(["read_key", "=", 'cc484439-b4de-493a-bf2e-27c413b00120']).\
            OR_WHERE(["read_key", "=", '57179e0c-1b53-47b9-94f3-475cdba60628']).\
            OR_WHERE(["read_key", "=", '7016622d-a4db-4ec0-8b97-85f6057317f1']).payload()
        result = store.query_tbl_with_payload("readings", payload)
        assert len(result["rows"]) == 3
        assert result["count"] == 3
        assert result["rows"][0]["read_key"] == "57179e0c-1b53-47b9-94f3-475cdba60628"
        assert result["rows"][1]["read_key"] == "cc484439-b4de-493a-bf2e-27c413b00120"
        assert result["rows"][2]["read_key"] == "7016622d-a4db-4ec0-8b97-85f6057317f1"

    def test_limit(self):
        payload = PayloadBuilder().LIMIT(1).payload()
        result = store.query_tbl_with_payload("statistics", payload)
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["key"] == "TEST_1"
        assert result["rows"][0]["description"] == "Testing the storage service data 1"
        assert result["rows"][0]["value"] == 10
        assert result["rows"][0]["previous_value"] == 2

    def test_offset(self):
        payload = PayloadBuilder().OFFSET(1).payload()
        assert json.dumps({"skip": 1}) == payload
        result = store.query_tbl_with_payload("statistics", payload)
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["key"] == "TEST_2"
        assert result["rows"][0]["description"] == "Testing the storage service data 2"
        assert result["rows"][0]["value"] == 15
        assert result["rows"][0]["previous_value"] == 2

    def test_limit_offset(self):
        payload = PayloadBuilder().LIMIT(2).OFFSET(1).payload()
        result = store.query_tbl_with_payload("statistics", payload)
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["key"] == "TEST_2"
        assert result["rows"][0]["description"] == "Testing the storage service data 2"
        assert result["rows"][0]["value"] == 15
        assert result["rows"][0]["previous_value"] == 2

    def test_default_order(self):
        payload = PayloadBuilder().ORDER_BY(["key"]).payload()
        result = store.query_tbl_with_payload("statistics", payload)
        assert len(result["rows"]) == 2
        assert result["count"] == 2
        assert result["rows"][0]["key"] == "TEST_1"

    def test_order(self):
        payload = PayloadBuilder().ORDER_BY(["key", "desc"]).payload()
        result = store.query_tbl_with_payload("statistics", payload)
        assert len(result["rows"]) == 2
        assert result["count"] == 2
        assert result["rows"][0]["key"] == "TEST_2"
        assert result["rows"][0]["description"] == "Testing the storage service data 2"
        assert result["rows"][0]["value"] == 15
        assert result["rows"][0]["previous_value"] == 2

    def test_multiple_order(self):
        payload = PayloadBuilder().ORDER_BY({"asset_code", "desc"}, {"read_key"}).payload()
        result = store.query_tbl_with_payload("readings", payload)
        assert len(result["rows"]) == 3
        assert result["count"] == 3
        assert result["rows"][0]["read_key"] == "57179e0c-1b53-47b9-94f3-475cdba60628"
        assert result["rows"][1]["read_key"] == "cc484439-b4de-493a-bf2e-27c413b00120"
        assert result["rows"][2]["read_key"] == "7016622d-a4db-4ec0-8b97-85f6057317f1"

    def test_aggregate(self):
        payload = PayloadBuilder().AGGREGATE(["max", "value"]).payload()
        result = store.query_tbl_with_payload("statistics", payload)
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["max_value"] == 15

    def test_multiple_aggregate(self):
        payload = PayloadBuilder().AGGREGATE(["min", "value"], ["max", "value"], ["avg", "value"]).payload()
        result = store.query_tbl_with_payload("statistics", payload)
        print(result)
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["min_value"] == 10
        assert result["rows"][0]["max_value"] == 15
        assert float(result["rows"][0]["avg_value"]) == 12.5

    def test_group(self):
        payload = PayloadBuilder().SELECT("previous_value").GROUP_BY("previous_value").payload()
        result = store.query_tbl_with_payload("statistics", payload)
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["previous_value"] == 2

    def test_aggregate_group(self):
        payload = PayloadBuilder().AGGREGATE(["min", "previous_value"]).GROUP_BY("previous_value") \
                .WHERE(["key", "=", "TEST_2"]).payload()
        result = store.query_tbl_with_payload("statistics", payload)
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["min_previous_value"] == 2
        assert result["rows"][0]["previous_value"] == 2

    @pytest.mark.skip(reason="No support from storage layer yet")
    def test_aggregate_group_having(self):
        pass

    @pytest.mark.skip(reason="FOGL-643")
    def test_select_json_data(self):
        # Example:
        # SELECT MIN(reading->>'sensor_code_2'), MAX(reading->>'sensor_code_2'), AVG((reading->>'sensor_code_2')::float) FROM readings WHERE asset_code = 'TEST_STORAGE_CLIENT';
        pass

    @pytest.mark.skip(reason="FOGL-640")
    def test_select_date(self):
        # Example:
        # SELECT user_ts FROM readings WHERE asset_code = 'asset_code' GROUP BY user_ts
        pass

    @pytest.mark.skip(reason="FOGL-637")
    def test_select_column_alias(self):
        # Example:
        # SELECT TO_CHAR(user_ts, 'YYYY-MM-DD HH24') as "timestamp" FROM readings GROUP BY TO_CHAR(user_ts, 'YYYY-MM-DD HH24');
        pass


@pytest.allure.feature("api")
@pytest.allure.story("storage client")
class TestStorageInsert:
    """This class tests INSERT queries of Storage layer using payload builder
    """
    def test_insert(self):
        payload = PayloadBuilder().INSERT(key='TEST_3', description="test", value='11', previous_value=2).payload()
        result = store.insert_into_tbl("statistics", payload)
        assert result == {'rows_affected': 1, 'response': 'inserted'}

    def test_invalid_insert(self):
        payload = PayloadBuilder().INSERT(key='TEST_3', value='11', previous_value=2).payload()
        result = store.insert_into_tbl("statistics", payload)
        assert "ERROR" in result["message"]

    def test_insert_json_data(self):
        payload = PayloadBuilder().INSERT(asset_code='TEST_STORAGE_CLIENT',
                                          read_key='74540500-0ac2-4166-afa7-9dd1a93a10e5'
                                          , reading='{"sensor_code_1": 90, "sensor_code_2": 6.9}').payload()
        result = store.insert_into_tbl("readings", payload)
        assert result == {'rows_affected': 1, 'response': 'inserted'}


@pytest.allure.feature("api")
@pytest.allure.story("storage client")
class TestStorageUpdate:
    """This class tests UPDATE queries of Storage layer using payload builder
    """
    def test_valid_update_with_condition(self):
        payload = PayloadBuilder().SET(value=90, description="Updated test value").\
            WHERE(["key", "=", "TEST_1"]).payload()
        result = store.update_tbl("statistics", payload)
        assert result == {'rows_affected': 1, 'response': 'updated'}

        # Assert that only one value is updated
        payload = PayloadBuilder().WHERE(["key", "=", "TEST_1"]).payload()
        result = store.query_tbl_with_payload("statistics", payload)
        assert result["rows"][0]["key"] == "TEST_1"
        assert result["rows"][0]["description"] == "Updated test value"
        assert result["rows"][0]["value"] == 90
        assert result["rows"][0]["previous_value"] == 2

        # Assert that other value is not updated
        payload = PayloadBuilder().WHERE(["key", "=", "TEST_2"]).payload()
        result = store.query_tbl_with_payload("statistics", payload)
        assert result["rows"][0]["key"] == "TEST_2"
        assert result["rows"][0]["description"] == "Testing the storage service data 2"
        assert result["rows"][0]["value"] == 15
        assert result["rows"][0]["previous_value"] == 2

    def test_invalid_key_update(self):
        payload = PayloadBuilder().SET(value=23, description="Updated test value 2").\
            WHERE(["key", "=", "bla"]).payload()
        result = store.update_tbl("statistics", payload)
        assert "No rows where updated" in result["message"]

        # Assert that values are not updated
        result = store.query_tbl("statistics")
        for r in result["rows"]:
            assert "Updated test value 2" != r["description"]

    def test_invalid_type_update(self):
        payload = PayloadBuilder().SET(value="invalid", description="Updated test value 3").\
            WHERE(["key", "=", "TEST_2"]).payload()
        # value column is of type int and we are trying to update with a string value
        result = store.update_tbl("statistics", payload)
        assert "ERROR" in result["message"]

        # Assert that values are not updated
        payload = PayloadBuilder().WHERE(["key", "=", "TEST_2"]).payload()
        result = store.query_tbl_with_payload("statistics", payload)
        assert result["rows"][0]["key"] == "TEST_2"
        assert result["rows"][0]["description"] == "Testing the storage service data 2"
        assert result["rows"][0]["value"] == 15
        assert result["rows"][0]["previous_value"] == 2

    def test_update_without_key(self):
        payload = PayloadBuilder().SET(value=1, description="Updated test value 4").payload()
        result = store.update_tbl("statistics", payload)
        assert result == {'rows_affected': 3, 'response': 'updated'}

        result = store.query_tbl("statistics")
        for r in result["rows"]:
            assert 1 == r["value"]
            assert "Updated test value 4" == r["description"]


@pytest.allure.feature("api")
@pytest.allure.story("storage client")
class TestStorageDelete:
    """This class tests DELETE queries of Storage layer using payload builder
    """
    def test_delete_with_key(self):
        payload = PayloadBuilder().WHERE(["key", "=", "TEST_1"]).payload()
        result = store.delete_from_tbl("statistics", payload)
        assert result == {'rows_affected': 1, 'response': 'deleted'}

        # Verify that row is actually deleted
        payload = PayloadBuilder().WHERE(["key", "=", "TEST_1"]).query_params()
        result = store.query_tbl("statistics", payload)
        assert len(result["rows"]) == 0
        assert result["count"] == 0

    def test_delete_with_invalid_key(self):
        payload = PayloadBuilder().WHERE(["key", "=", "TEST_invalid"]).payload()
        result = store.delete_from_tbl("statistics", payload)
        assert result == {'rows_affected': 0, 'response': 'deleted'}

        # Verify that no row is deleted
        result = store.query_tbl("statistics")
        assert len(result["rows"]) == 2
        assert result["count"] == 2
        assert result["rows"][0]["key"] == "TEST_2"
        assert result["rows"][1]["key"] == "TEST_3"

    def test_delete_all(self):
        result = store.delete_from_tbl("statistics", {})
        assert result == {'rows_affected': 2, 'response': 'deleted'}

        # Verify that all rows are deleted
        result = store.query_tbl("statistics")
        assert len(result["rows"]) == 0
        assert result["count"] == 0
