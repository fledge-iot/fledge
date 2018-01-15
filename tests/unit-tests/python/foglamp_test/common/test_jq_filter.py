"""The following tests the jq filter component"""
import pytest
import asyncio
import uuid
import random
import json
from datetime import datetime, timezone

from foglamp.common.jqfilter import JQFilter
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.storage_client import StorageClient, ReadingsStorageClient

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

pytestmark = pytest.mark.asyncio


@pytest.allure.feature("integration")
@pytest.allure.story("jq filter testing")
class TestJQFilter:
    """
    JQ Filter Tests
      - Test that north plugins can load and apply JQ filter
      - Test that correct results are returned after applying JQ filter
    """
    _name = "JQFilter"
    # TODO: How to eliminate manual intervention as below when tests will run unattended at CI?
    _core_management_port = 43643
    _core_management_host = "localhost"

    _storage_client = StorageClient("localhost", _core_management_port)
    _readings = ReadingsStorageClient("localhost", _core_management_port)
    _cfg_manager = ConfigurationManager(_storage_client)

    # Configuration related to JQ Filter
    _CONFIG_CATEGORY_NAME ="JQ_FILTER"
    _CONFIG_CATEGORY_DESCRIPTION = "JQ configuration"
    _DEFAULT_FILTER_CONFIG = {
        "applyFilter": {
            "description": "Whether to apply filter before processing the data",
            "type": "boolean",
            "default": "False"
        },
        "filterRule": {
            "description": "JQ formatted filter to apply (applicable if applyFilter is True)",
            "type": "string",
            "default": ".[]"
        }
    }
    _first_read_id = None
    _raw_data = None
    _jqfilter = JQFilter()

    @classmethod
    def set_configuration(cls):
        """" set the default configuration for plugin
        :return:
            Configuration information that will be set for any north plugin
        """
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(cls._cfg_manager.create_category(cls._CONFIG_CATEGORY_NAME,
                                                                       cls._DEFAULT_FILTER_CONFIG,
                                                                       cls._CONFIG_CATEGORY_DESCRIPTION))
        return event_loop.run_until_complete(cls._cfg_manager.get_category_all_items(cls._CONFIG_CATEGORY_NAME))

    @classmethod
    @pytest.fixture(scope="class", autouse=True)
    def init_test(cls):
        """Setup and Cleanup method, executed once for the entire test class"""
        cls.set_configuration()
        cls._first_read_id = cls._insert_readings_data()
        cls._insert_readings_data()
        payload = PayloadBuilder()\
            .WHERE(['id', '>=', cls._first_read_id]) \
            .ORDER_BY(['id', 'ASC']) \
            .payload()
        readings = cls._readings.query(payload)
        cls._raw_data = readings['rows']

        yield
        # Delete all test data from readings and configuration
        cls._storage_client.delete_from_tbl("readings", {})
        payload = PayloadBuilder().WHERE(["key", "=", cls._CONFIG_CATEGORY_NAME]).payload()
        cls._storage_client.delete_from_tbl("configuration", payload)

    @classmethod
    def _insert_readings_data(cls):
        """Insert reads in readings table
        args:

        :return:
            The id of inserted row

        """
        readings = []

        read = dict()
        read["asset_code"] = "TEST_JQ"
        read["read_key"] = str(uuid.uuid4())
        read['reading'] = dict()
        read['reading']['rate'] = random.randint(1, 100)
        ts = str(datetime.now(tz=timezone.utc))
        read["user_ts"] = ts

        readings.append(read)

        payload = dict()
        payload['readings'] = readings

        cls._readings.append(json.dumps(payload))

        payload = PayloadBuilder().AGGREGATE(["max", "id"]).payload()
        result = cls._storage_client.query_tbl_with_payload("readings", payload)
        return int(result["rows"][0]["max_id"])

    async def test_default_filter_configuration(self):
        """Test that filter is not applied when testing with default configuration"""
        apply_filter = await self._cfg_manager.get_category_item_value_entry(self._CONFIG_CATEGORY_NAME, 'applyFilter')
        jq_rule = await self._cfg_manager.get_category_item_value_entry(self._CONFIG_CATEGORY_NAME, 'filterRule')
        if apply_filter.upper() == "TRUE":
            transformed_data = self._jqfilter.transform(self._raw_data, jq_rule)
            assert transformed_data is None
        else:
            assert True

    async def test_default_filterRule(self):
        """Test that filter is applied and returns readings block unaltered with default configuration of filterRule"""
        await self._cfg_manager.set_category_item_value_entry(self._CONFIG_CATEGORY_NAME, 'applyFilter', "True")
        apply_filter = await self._cfg_manager.get_category_item_value_entry(self._CONFIG_CATEGORY_NAME, 'applyFilter')
        jq_rule = await self._cfg_manager.get_category_item_value_entry(self._CONFIG_CATEGORY_NAME, 'filterRule')
        if apply_filter.upper() == "TRUE":
            transformed_data = self._jqfilter.transform(self._raw_data, jq_rule)
            assert transformed_data == self._raw_data
        else:
            assert False

    async def test_custom_filter_configuration(self):
        """Test with supplied filterRule"""
        await self._cfg_manager.set_category_item_value_entry(self._CONFIG_CATEGORY_NAME, 'applyFilter', "True")
        await self._cfg_manager.set_category_item_value_entry(self._CONFIG_CATEGORY_NAME,
                                                              'filterRule', ".[0]|{Measurement_id: .id}")
        apply_filter = await self._cfg_manager.get_category_item_value_entry(self._CONFIG_CATEGORY_NAME, 'applyFilter')
        jq_rule = await self._cfg_manager.get_category_item_value_entry(self._CONFIG_CATEGORY_NAME, 'filterRule')
        transformed_data = self._jqfilter.transform(self._raw_data, jq_rule)
        if apply_filter.upper() == "TRUE":
            assert transformed_data == [{"Measurement_id": self._first_read_id}]
        else:
            assert False

    async def test_invalid_filter_configuration(self):
        """Test with invalid filterRule"""
        await self._cfg_manager.set_category_item_value_entry(self._CONFIG_CATEGORY_NAME, 'filterRule', "|")
        jq_rule = await self._cfg_manager.get_category_item_value_entry(self._CONFIG_CATEGORY_NAME, 'filterRule')
        with pytest.raises(ValueError) as ex:
            self._jqfilter.transform(self._raw_data, jq_rule)
        assert "jq: error: syntax error, unexpected '|'" in str(ex)
