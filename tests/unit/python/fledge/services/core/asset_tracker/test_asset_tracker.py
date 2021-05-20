# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
from unittest.mock import MagicMock, patch
import pytest
import sys
import asyncio

from fledge.services.core.asset_tracker.asset_tracker import AssetTracker
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.configuration_manager import ConfigurationManager

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("services", "core", "asset-tracker")
class TestAssetTracker:

    async def test_init_with_no_storage(self):
        storage_client_mock = None
        with pytest.raises(TypeError) as excinfo:
            AssetTracker(storage_client_mock)
        assert 'Must be a valid Async Storage object' == str(excinfo.value)

    @pytest.mark.parametrize("result, asset_list", [
        ({'rows': [], 'count': 0}, []),
        ({'rows': [{'event': 'Ingest', 'service': 'sine', 'plugin': 'sinusoid', 'asset': 'sinusoid'}], 'count': 1}, [{'event': 'Ingest', 'service': 'sine', 'asset': 'sinusoid', 'plugin': 'sinusoid'}])
    ])
    async def test_load_asset_records(self, result, asset_list):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        asset_tracker = AssetTracker(storage_client_mock)
        asset_tracker._registered_asset_records = []

        async def mock_coro():
            return result

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await mock_coro()
        else:
            _rv = asyncio.ensure_future(mock_coro())

        with patch.object(asset_tracker._storage, 'query_tbl_with_payload', return_value=_rv) as patch_query_tbl:
            await asset_tracker.load_asset_records()
            assert asset_list == asset_tracker._registered_asset_records
        patch_query_tbl.assert_called_once_with('asset_tracker', '{"return": ["asset", "event", "service", "plugin"]}')

    async def test_add_asset_record(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        asset_tracker = AssetTracker(storage_client_mock)
        cfg_manager = ConfigurationManager(storage_client_mock)
        asset_tracker._registered_asset_records = []
        payload = {"plugin": "sinusoid", "asset": "sinusoid", "event": "Ingest", "fledge": "Fledge", "service": "sine"}

        async def mock_coro():
            return {"default": "Fledge", "value": "Fledge", "type": "string", "description": "Name of this Fledge service"}

        async def mock_coro2():
            return {"response": "inserted", "rows_affected": 1}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await mock_coro()
            _rv2 = await mock_coro2()
        else:
            _rv1 = asyncio.ensure_future(mock_coro())
            _rv2 = asyncio.ensure_future(mock_coro2())

        with patch.object(cfg_manager, 'get_category_item', return_value=_rv1) as patch_get_cat_item:
            with patch.object(asset_tracker._storage, 'insert_into_tbl', return_value=_rv2) as patch_insert_tbl:
                result = await asset_tracker.add_asset_record(asset='sinusoid', event='Ingest', service='sine', plugin='sinusoid')
                assert payload == result
            args, kwargs = patch_insert_tbl.call_args
            assert 'asset_tracker' == args[0]
            assert payload == json.loads(args[1])
        patch_get_cat_item.assert_called_once_with(category_name='service', item_name='name')

    # TODO: will add -ve tests later
