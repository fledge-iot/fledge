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


@pytest.allure.feature("integration")
@pytest.allure.story("jq filter testing")
class TestJQFilter:
    """
    JQ Filter Tests
      - Test that north plugins can load and apply JQ filter
      - Test that correct results are returned after applying JQ filter
    """
    _name = "JQFilter"
    _core_management_port = 37685
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

    @classmethod
    def set_configuration(cls):
        """" set the default configuration for plugin
        :return:
            Configuration information that was set for any north plugin
        """
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(cls._cfg_manager.create_category(cls._CONFIG_CATEGORY_NAME,
                                                                       cls._DEFAULT_FILTER_CONFIG,
                                                                       cls._CONFIG_CATEGORY_DESCRIPTION))
        return event_loop.run_until_complete(cls._cfg_manager.get_category_all_items(cls._CONFIG_CATEGORY_NAME))

    @classmethod
    @pytest.fixture(autouse=True)
    def init_test(cls):
        """Setup and Cleanup method, called after every test"""
        cls.set_configuration()
        yield
        # Delete all test data from readings and logs
        # cls._storage_client.delete_from_tbl("readings", {})

    @classmethod
    def _insert_readings_data(cls):
        """Insert reads in readings table with specified time delta of user_ts (in hours)
        args:
            hours_delta: delta of user_ts (in hours)
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

    @pytest.mark.asyncio
    async def test_default(self):
        jqfilter = JQFilter()
        id1 = self._insert_readings_data()
        id2 = self._insert_readings_data()
        apply_filter = await self._cfg_manager.get_category_item(self._CONFIG_CATEGORY_NAME,
                                                           self._DEFAULT_FILTER_CONFIG['applyFilter'])
        jq_rule = await self._cfg_manager.get_category_item(self._CONFIG_CATEGORY_NAME,
                                                      self._DEFAULT_FILTER_CONFIG['filterRule'])
        reading_block = self._readings.fetch(id1, 2)
        print("\napply_filter:{}\n, reading_block:{}\n,jq_rule:{}\n".format(apply_filter, reading_block, jq_rule))
        transformed_data = jqfilter.transform(apply_filter, reading_block, jq_rule)
        assert transformed_data == reading_block
