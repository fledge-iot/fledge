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
@pytest.allure.story("storage")
class TestStorageRead:
    """
    This class tests SELECT (Read) queries of Storage layer using payload builder
    """
    def test_select(self):
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().SELECT().payload())
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
        result = Storage().query_tbl("statistics", PayloadBuilder().WHERE(["key", "=", "TEST_1"]).query_params())
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["key"] == "TEST_1"
        assert result["rows"][0]["description"] == "Testing the storage service data 1"
        assert result["rows"][0]["value"] == 10
        assert result["rows"][0]["previous_value"] == 2

    def test_where_payload(self):
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().WHERE(["value", "!=", 15]).payload())
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["key"] == "TEST_1"
        assert result["rows"][0]["description"] == "Testing the storage service data 1"
        assert result["rows"][0]["value"] == 10
        assert result["rows"][0]["previous_value"] == 2

    @pytest.mark.skip(reason="FOGL-615")
    def test_where_invalid_key(self):
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().
                                                  WHERE(["bla", "=", "invalid"]).payload())
        assert "ERROR" in result["message"]

    @pytest.mark.skip(reason="FOGL-607 #7")
    def test_multiple_and_where(self):
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().
                                                  WHERE(["value", "!=", 0]).
                                                  AND_WHERE(["key", "=", "TEST_1"]).
                                                  AND_WHERE(["previous_value", "<", 10]).payload())
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["key"] == "TEST_1"
        assert result["rows"][0]["description"] == "Testing the storage service data 1"
        assert result["rows"][0]["value"] == 10
        assert result["rows"][0]["previous_value"] == 2

    @pytest.mark.skip(reason="FOGL-607 #7")
    def test_multiple_or_where(self):
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().
                                                  WHERE(["value", "=", 0]).
                                                  OR_WHERE(["key", "=", "TEST_1"]).
                                                  OR_WHERE(["previous_value", ">", 10]).payload())
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["key"] == "TEST_1"
        assert result["rows"][0]["description"] == "Testing the storage service data 1"
        assert result["rows"][0]["value"] == 10
        assert result["rows"][0]["previous_value"] == 2

    def test_limit(self):
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().LIMIT(1).payload())
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["key"] == "TEST_1"
        assert result["rows"][0]["description"] == "Testing the storage service data 1"
        assert result["rows"][0]["value"] == 10
        assert result["rows"][0]["previous_value"] == 2

    def test_offset(self):
        payload = PayloadBuilder().OFFSET(1).payload()
        assert json.dumps({"skip": 1}) == payload
        result = Storage().query_tbl_with_payload("statistics", payload)
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["key"] == "TEST_2"
        assert result["rows"][0]["description"] == "Testing the storage service data 2"
        assert result["rows"][0]["value"] == 15
        assert result["rows"][0]["previous_value"] == 2

    def test_limit_offset(self):
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().LIMIT(2).OFFSET(1).payload())
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["key"] == "TEST_2"
        assert result["rows"][0]["description"] == "Testing the storage service data 2"
        assert result["rows"][0]["value"] == 15
        assert result["rows"][0]["previous_value"] == 2

    def test_default_order(self):
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().
                                                  ORDER_BY(["key"]).payload())
        assert len(result["rows"]) == 2
        assert result["count"] == 2
        assert result["rows"][0]["key"] == "TEST_1"

    def test_order(self):
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().
                                                  ORDER_BY(["key", "desc"]).payload())
        assert len(result["rows"]) == 2
        assert result["count"] == 2
        assert result["rows"][0]["key"] == "TEST_2"
        assert result["rows"][0]["description"] == "Testing the storage service data 2"
        assert result["rows"][0]["value"] == 15
        assert result["rows"][0]["previous_value"] == 2

    def test_aggregate(self):
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().
                                                  AGGREGATE(["max", "value"]).payload())
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["max_value"] == 15

    @pytest.mark.skip(reason="FOGL-617")
    def test_group(self):
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().SELECT("previous_value").
                                                  GROUP_BY("previous_value").payload())
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["previous_value"] == 2

    def test_aggregate_group(self):
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().
                                                  AGGREGATE(["min", "previous_value"]).
                                                  GROUP_BY("previous_value").payload())
        assert len(result["rows"]) == 1
        assert result["count"] == 1
        assert result["rows"][0]["min_previous_value"] == 2
        assert result["rows"][0]["previous_value"] == 2


@pytest.allure.feature("api")
@pytest.allure.story("storage")
class TestStorageInsert:
    """
    This class tests INSERT queries of Storage layer using payload builder
    """
    def test_valid_insert(self):
        result = Storage().insert_into_tbl("statistics",  PayloadBuilder().
                                           INSERT(key='TEST_3', description="test", value='11', previous_value=2).
                                           payload())
        assert result == {'response': 'inserted'}

    @pytest.mark.skip(reason="FOGL-615")
    def test_invalid_insert(self):
        result = Storage().insert_into_tbl("statistics",  PayloadBuilder().
                                           INSERT(key='TEST_3', value='11', previous_value=2).payload())
        assert "ERROR" in result["message"]


@pytest.allure.feature("api")
@pytest.allure.story("storage")
class TestStorageUpdate:
    """
    This class tests UPDATE queries of Storage layer using payload builder
    """
    @pytest.mark.skip(reason="FOGL-616")
    def test_valid_update_with_condition(self):
        result = Storage().update_tbl("statistics", PayloadBuilder().
                                      SET(value=90, description="Updated test value").
                                      WHERE(["key", "=", "TEST_1"]).payload())
        assert result == {'response': 'updated'}
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().SELECT_ALL().payload())

        # Assert that only one value is updated
        assert result["rows"][0]["key"] == "TEST_1"
        assert result["rows"][0]["description"] == "Updated test value"
        assert result["rows"][0]["value"] == 90
        assert result["rows"][0]["previous_value"] == 2

        # Assert that other value is not updated
        assert result["rows"][1]["key"] == "TEST_2"
        assert result["rows"][1]["description"] == "Testing the storage service data 2"
        assert result["rows"][1]["value"] == 15
        assert result["rows"][1]["previous_value"] == 2

    @pytest.mark.skip(reason="FOGL-616")
    def test_invalid_key_update(self):
        result = Storage().update_tbl("statistics", PayloadBuilder().
                                      SET(value=23, description="Updated test value 2").
                                      WHERE(["key", "=", "bla"]).payload())
        assert "ERROR" in result["message"]

        # Assert that values are not updated (Check any single record)
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().
                                                  WHERE(["key", "=", "TEST_2"]).payload())
        assert result["rows"][0]["key"] == "TEST_2"
        assert result["rows"][0]["description"] == "Testing the storage service data 2"
        assert result["rows"][0]["value"] == 15
        assert result["rows"][0]["previous_value"] == 2

    @pytest.mark.skip(reason="FOGL-615")
    def test_invalid_type_update(self):
        result = Storage().update_tbl("statistics", PayloadBuilder().
                                      SET(value="invalid", description="Updated test value 3").
                                      WHERE(["key", "=", "TEST_2"]).payload())
        assert "ERROR" in result["message"]

        # Assert that values are not updated
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().
                                                  WHERE(["key", "=", "TEST_2"]).payload())
        assert result["rows"][0]["key"] == "TEST_2"
        assert result["rows"][0]["description"] == "Testing the storage service data 2"
        assert result["rows"][0]["value"] == 15
        assert result["rows"][0]["previous_value"] == 2

    def test_update_without_key(self):
        result = Storage().update_tbl("statistics", PayloadBuilder().
                                      SET(value=1, description="Updated test value 4").payload())
        assert result == {'response': 'updated'}
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().SELECT_ALL().payload())
        for _i in range(len(result["rows"])):
            assert result["rows"][_i]["value"] == 1
            assert result["rows"][_i]["description"] == "Updated test value 4"


@pytest.allure.feature("api")
@pytest.allure.story("storage")
class TestStorageDelete:
    """
    This class tests DELETE queries of Storage layer using payload builder
    """
    def test_valid_delete_with_key(self):
        result = Storage().delete_from_tbl("statistics", PayloadBuilder().WHERE(["key", "=", "TEST_1"]).payload())
        assert result == {'response': 'deleted'}

        # Verify that row is actually deleted
        result = Storage().query_tbl("statistics", PayloadBuilder().WHERE(["key", "=", "TEST_1"]).query_params())
        assert len(result["rows"]) == 0
        assert result["count"] == 0

    def test_delete_with_invalid_key(self):
        result = Storage().delete_from_tbl("statistics", PayloadBuilder().
                                           WHERE(["key", "=", "TEST_invalid"]).payload())

        # FIXME: Is deleted the correct response?
        assert result == {'response': 'deleted'}

        # Verify that no row is deleted
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().SELECT_ALL().payload())
        assert len(result["rows"]) == 2
        assert result["count"] == 2
        assert result["rows"][0]["key"] == "TEST_2"
        assert result["rows"][1]["key"] == "TEST_3"

    def test_delete_all(self):
        result = Storage().delete_from_tbl("statistics", {})
        assert result == {'response': 'deleted'}

        # Verify that all rows are deleted
        result = Storage().query_tbl_with_payload("statistics", PayloadBuilder().SELECT_ALL().payload())
        assert len(result["rows"]) == 0
        assert result["count"] == 0
