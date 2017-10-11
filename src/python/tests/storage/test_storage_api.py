# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END
import pytest
import os
import py
from foglamp.storage.payload_builder import PayloadBuilder

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# TODO: remove once self registration is done
from foglamp.core.service_registry.service_registry import Service
from foglamp.storage.storage import Storage

Service.Instances.register(name="store", s_type="Storage", address="0.0.0.0", port=8080, management_port=8092)

# TODO: remove once FOGL-510 is done
@pytest.fixture(scope="module", autouse=True)
def create_init_data(request):
    """
    Module level fixture that is called once for the test
        Before the tests starts, it creates the init data
        After all the tests, it clears database and sets the init data
    Fixture called by default (autouse=False)
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
    def test_select(self):
        res = Storage().query_tbl_with_payload("statistics", PayloadBuilder().SELECT().payload())
        assert len(res["rows"]) == 2
        assert res["count"] == 2
        assert res["rows"][0]["key"] == "TEST_1"
        assert res["rows"][0]["description"] == "Testing the storage service data 1"
        assert res["rows"][0]["value"] == 10
        assert res["rows"][0]["previous_value"] == 1

        assert res["rows"][1]["key"] == "TEST_2"
        assert res["rows"][1]["description"] == "Testing the storage service data 2"
        assert res["rows"][1]["value"] == 15
        assert res["rows"][1]["previous_value"] == 2

    def test_where_query_param(self):
        res = Storage().query_tbl("statistics", PayloadBuilder().WHERE(["key", "=", "TEST_1"]).query_params())
        assert len(res["rows"]) == 1
        assert res["count"] == 1
        assert res["rows"][0]["key"] == "TEST_1"
        assert res["rows"][0]["description"] == "Testing the storage service data 1"
        assert res["rows"][0]["value"] == 10
        assert res["rows"][0]["previous_value"] == 1

    def test_where_payload(self):
        res = Storage().query_tbl_with_payload("statistics", PayloadBuilder().WHERE(["value", "!=", 15]).payload())
        assert len(res["rows"]) == 1
        assert res["count"] == 1
        assert res["rows"][0]["key"] == "TEST_1"
        assert res["rows"][0]["description"] == "Testing the storage service data 1"
        assert res["rows"][0]["value"] == 10
        assert res["rows"][0]["previous_value"] == 1


@pytest.allure.feature("api")
@pytest.allure.story("storage")
class TestStorageInsert:
    pass


@pytest.allure.feature("api")
@pytest.allure.story("storage")
class TestStorageUpdate:
    pass


@pytest.allure.feature("api")
@pytest.allure.story("storage")
class TestStorageDelete:
    pass
