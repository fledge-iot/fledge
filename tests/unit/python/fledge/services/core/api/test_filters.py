# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import asyncio
import json
from unittest.mock import MagicMock, patch, call
from aiohttp import web
import pytest
import sys

from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.services.core import connect, routes
from fledge.services.core.api import filters, utils as apiutils
from fledge.services.core.api.filters import _LOGGER
from fledge.services.core.api.plugins import common

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestFilters:

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def async_mock(self, return_val):
        return return_val

    async def test_get_filters(self, client):
        async def get_filters():
            return {"rows": []}

        storage_client_mock = MagicMock(StorageClientAsync)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await get_filters()
        else:
            _rv = asyncio.ensure_future(get_filters())
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=_rv) as query_tbl_patch:
                resp = await client.get('/fledge/filter')
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert {'filters': []} == json_response
            query_tbl_patch.assert_called_once_with('filters')

    async def test_get_filters_storage_exception(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', side_effect=StorageServerError(
                    None, None, error='something went wrong')) as query_tbl_patch:
                with patch.object(_LOGGER, 'error') as patch_logger:
                    resp = await client.get('/fledge/filter')
                    assert 500 == resp.status
                    assert "something went wrong" == resp.reason
                assert 1 == patch_logger.call_count
                args, kwargs = patch_logger.call_args
                assert 'Get all filters, caught storage exception: {}'.format('something went wrong') in args[0]
            query_tbl_patch.assert_called_once_with('filters')

    async def test_get_filters_exception(self, client):
        async def get_filters():
            return {"count": 1}

        storage_client_mock = MagicMock(StorageClientAsync)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await get_filters()
        else:
            _rv = asyncio.ensure_future(get_filters())
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=_rv) as query_tbl_patch:
                with patch.object(_LOGGER, 'error') as patch_logger:
                    resp = await client.get('/fledge/filter')
                    assert 500 == resp.status
                    assert "'rows'" == resp.reason
                assert 1 == patch_logger.call_count
            query_tbl_patch.assert_called_once_with('filters')

    async def test_get_filter_by_name(self, client):
        async def q_result(*args):
            table = args[0]
            payload = args[1]

            if table == 'filters':
                assert {"where": {"column": "name", "condition": "=", "value": filter_name}} == json.loads(payload)
                return {'count': 1, 'rows': [{'name': filter_name, 'plugin': 'python35'}]}

            if table == 'filter_users':
                assert {"where": {"column": "name", "condition": "=", "value": filter_name}} == json.loads(payload)
                return {'count': 0, 'rows': []}

        filter_name = "AssetFilter"
        cat_info = {'plugin': {'description': 'Python 3.5 filter plugin', 'type': 'string', 'default': 'python35', 'value': 'python35'},
                    'config': {'description': 'Python 3.5 filter configuration.', 'type': 'JSON', 'default': '{}', 'value': '{}'},
                    'script': {'description': 'Python 3.5 module to load.', 'type': 'script', 'default': '', 'value': ''}}

        result = {"filter": {"config": cat_info, "name": filter_name, "plugin": "python35", "users": []}}
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await self.async_mock(cat_info)
        else:
            _rv = asyncio.ensure_future(self.async_mock(cat_info))
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                    resp = await client.get('/fledge/filter/{}'.format(filter_name))
                    assert 200 == resp.status
                    r = await resp.text()
                    json_response = json.loads(r)
                    assert result == json_response
            get_cat_info_patch.assert_called_once_with(filter_name)

    async def test_get_filter_by_name_not_found(self, client):
        filter_name = "AssetFilter"
        cat_info = {'plugin': {'description': 'Python 3.5 filter plugin', 'type': 'string', 'default': 'python35', 'value': 'python35'},
                    'config': {'description': 'Python 3.5 filter configuration.', 'type': 'JSON', 'default': '{}', 'value': '{}'},
                    'script': {'description': 'Python 3.5 module to load.', 'type': 'script', 'default': '', 'value': ''}}

        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        filter_result = {'count': 0, 'rows': []}
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await self.async_mock(cat_info)
            _rv2 = await self.async_mock(filter_result)
        else:
            _rv1 = asyncio.ensure_future(self.async_mock(cat_info))
            _rv2 = asyncio.ensure_future(self.async_mock(filter_result))
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv1) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=_rv2) as query_tbl_with_payload_patch:
                    resp = await client.get('/fledge/filter/{}'.format(filter_name))
                    assert 404 == resp.status
                    assert "No such filter '{}' found.".format(filter_name) == resp.reason
                query_tbl_with_payload_patch.assert_called_once_with('filters', '{"where": {"column": "name", "condition": "=", "value": "AssetFilter"}}')
            get_cat_info_patch.assert_called_once_with(filter_name)

    async def test_get_filter_by_name_value_error(self, client):
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await self.async_mock(None)
        else:
            _rv = asyncio.ensure_future(self.async_mock(None))
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv) as get_cat_info_patch:
                resp = await client.get('/fledge/filter/{}'.format(filter_name))
                assert 404 == resp.status
                assert "No such 'AssetFilter' category found." == resp.reason
            get_cat_info_patch.assert_called_once_with(filter_name)

    async def test_get_filter_by_name_storage_error(self, client):
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', side_effect=StorageServerError(
                    None, None, error='something went wrong')) as get_cat_info_patch:
                with patch.object(_LOGGER, 'error') as patch_logger:
                    resp = await client.get('/fledge/filter/{}'.format(filter_name))
                    assert 500 == resp.status
                    assert "something went wrong" == resp.reason
                assert 1 == patch_logger.call_count
                args, kwargs = patch_logger.call_args
                assert 'Failed to get filter name: {}. Storage error occurred: {}'.format(
                    filter_name, 'something went wrong') in args[0]
            get_cat_info_patch.assert_called_once_with(filter_name)

    async def test_get_filter_by_name_type_error(self, client):
        # What cause a TypeError https://github.com/fledge-iot/fledge/blob/develop/python/fledge/services/core/api/filters.py#L319
        storage_client_mock = MagicMock(StorageClientAsync)
        filter_name = "AssetFilter"        
        cf_mgr = ConfigurationManager(storage_client_mock)        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', side_effect=TypeError) as get_cat_info_patch:
                resp = await client.get('/fledge/filter/{}'.format(filter_name))
                assert 400 == resp.status
                # assert "?" == resp.reason
            get_cat_info_patch.assert_called_once_with(filter_name)

    async def test_get_filter_by_name_exception(self, client):
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', side_effect=Exception) as get_cat_info_patch:
                with patch.object(_LOGGER, 'error') as patch_logger:
                    resp = await client.get('/fledge/filter/{}'.format(filter_name))
                    assert 500 == resp.status
                    assert resp.reason is ''
                assert 1 == patch_logger.call_count
            get_cat_info_patch.assert_called_once_with(filter_name)

    @pytest.mark.parametrize("data", [
        {},
        {"name": "test"},
        {"plugin": "benchmark"},
        {"blah": "blah"}
    ])
    async def test_bad_create_filter(self, client, data):
        msg = "Filter name, plugin name are mandatory."
        resp = await client.post('/fledge/filter'.format("bench"), data=json.dumps(data))
        assert 400 == resp.status
        assert msg == resp.reason

    async def test_create_filter_value_error_1(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await self.async_mock({"result": "test"})
        else:
            _rv = asyncio.ensure_future(self.async_mock({"result": "test"}))        
        msg = "This 'test' filter already exists"
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv) as get_cat_info_patch:
                resp = await client.post('/fledge/filter'.format("bench"), data=json.dumps(
                    {"name": "test", "plugin": "benchmark"}))
                assert 404 == resp.status
                assert msg == resp.reason
            get_cat_info_patch.assert_called_once_with(category_name='test')

    async def test_create_filter_value_error_2(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        plugin_name = 'benchmark'
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await self.async_mock(None)
        else:
            _rv = asyncio.ensure_future(self.async_mock(None))
        msg = "Can not get 'plugin_info' detail from plugin '{}'".format(plugin_name)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv) as get_cat_info_patch:
                with patch.object(apiutils, 'get_plugin_info', return_value=None) as api_utils_patch:
                    with patch.object(common._logger, 'warning') as patch_logger:
                        resp = await client.post('/fledge/filter'.format("bench"), data=json.dumps(
                            {"name": "test", "plugin": plugin_name}))
                        assert 404 == resp.status
                        assert msg == resp.reason
                    assert 2 == patch_logger.call_count
                api_utils_patch.assert_called_once_with(plugin_name, dir='filter')
            get_cat_info_patch.assert_called_once_with(category_name='test')

    async def test_create_filter_value_error_3(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        plugin_name = 'benchmark'
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await self.async_mock(None)
        else:
            _rv = asyncio.ensure_future(self.async_mock(None))
        msg = "Loaded plugin 'python35', type 'south', doesn't match the specified one '{}', type 'filter'".format(
            plugin_name)
        ret_val = {"config": {'plugin': {'description': 'Python 3.5 filter plugin', 'type': 'string',
                                         'default': 'python35'}}, "type": "south"}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv) as get_cat_info_patch:
                with patch.object(apiutils, 'get_plugin_info', return_value=ret_val) as api_utils_patch:
                    with patch.object(common._logger, 'warning') as patch_logger:
                        resp = await client.post('/fledge/filter'.format("bench"), data=json.dumps(
                            {"name": "test", "plugin": plugin_name}))
                        assert 404 == resp.status
                        assert msg == resp.reason
                    assert 2 == patch_logger.call_count
                api_utils_patch.assert_called_once_with(plugin_name, dir='filter')
            get_cat_info_patch.assert_called_once_with(category_name='test')

    async def test_create_filter_value_error_4(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        plugin_name = 'filter'
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await self.async_mock(None)
            _rv2 = await self.async_mock({'count': 0, 'rows': []})
        else:
            _rv1 = asyncio.ensure_future(self.async_mock(None))
            _rv2 = asyncio.ensure_future(self.async_mock({'count': 0, 'rows': []}))
        msg = "filter_config must be a JSON object"
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv1) as get_cat_info_patch:
                with patch.object(apiutils, 'get_plugin_info', return_value={"config": {'plugin': {'description': 'Python 3.5 filter plugin', 'type': 'string', 'default': 'filter'}}, "type": "filter"}) as api_utils_patch:
                    with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=_rv2) as query_tbl_patch:
                        with patch.object(storage_client_mock, 'insert_into_tbl', return_value=_rv1) as insert_tbl_patch:
                            with patch.object(cf_mgr, 'create_category', return_value=_rv1) as create_cat_patch:
                                with patch.object(common._logger, 'warning') as patch_logger:
                                    resp = await client.post('/fledge/filter'.format("bench"), data=json.dumps(
                                        {"name": "test", "plugin": plugin_name, "filter_config": "blah"}))
                                    assert 404 == resp.status
                                    assert msg == resp.reason
                                assert 2 == patch_logger.call_count
                            create_cat_patch.assert_called_once_with(
                                category_description="Configuration of 'test' filter for plugin 'filter'",
                                category_name='test', category_value=
                                {'plugin': {'description': 'Python 3.5 filter plugin', 'type': 'string',
                                            'default': 'filter'}}, keep_original_items=True)
                        args, kwargs = insert_tbl_patch.call_args_list[0]
                        assert 'filters' == args[0]
                        assert {"name": "test", "plugin": "filter"} == json.loads(args[1])
                        # insert_tbl_patch.assert_called_once_with('filters', '{"name": "test", "plugin": "filter"}')
                    args, kwargs = query_tbl_patch.call_args_list[0]
                    assert 'filters' == args[0]
                    assert {"where": {"column": "name", "condition": "=", "value": "test"}} == json.loads(args[1])
                    # query_tbl_patch.assert_called_once_with('filters', '{"where": {"column": "name", "condition": "=", "value": "test"}}')
                api_utils_patch.assert_called_once_with(plugin_name, dir='filter')
            get_cat_info_patch.assert_called_once_with(category_name='test')

    async def test_create_filter_storage_error(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        plugin_name = 'filter'
        name = 'test'
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await self.async_mock(None)
        else:
            _rv = asyncio.ensure_future(self.async_mock(None))
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv) as get_cat_info_patch:
                with patch.object(apiutils, 'get_plugin_info', return_value={
                    "config": {'plugin': {'description': 'Python 3.5 filter plugin', 'type': 'string',
                                          'default': 'filter'}}, "type": "filter"}) as api_utils_patch:
                    with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=StorageServerError(
                            None, None, error='something went wrong')):
                        with patch.object(filters, '_delete_configuration_category', return_value=_rv) as _delete_cfg_patch:
                            with patch.object(_LOGGER, 'error') as patch_logger:
                                with patch.object(common._logger, 'warning') as patch_logger2:
                                    resp = await client.post('/fledge/filter'.format("bench"), data=json.dumps(
                                        {"name": name, "plugin": plugin_name}))
                                    assert 500 == resp.status
                                    assert 'something went wrong' == resp.reason
                                assert 2 == patch_logger2.call_count
                            assert 1 == patch_logger.call_count
                        args, kwargs = _delete_cfg_patch.call_args
                        assert name == args[1]
                api_utils_patch.assert_called_once_with(plugin_name, dir='filter')
            get_cat_info_patch.assert_called_once_with(category_name=name)

    async def test_create_filter_exception(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        plugin_name = 'filter'
        name = 'test'
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', side_effect=Exception) as get_cat_info_patch:
                with patch.object(_LOGGER, 'error') as patch_logger:
                    resp = await client.post('/fledge/filter'.format("bench"), data=json.dumps(
                        {"name": name, "plugin": plugin_name}))
                    assert 500 == resp.status
                    assert resp.reason is ''
                assert 1 == patch_logger.call_count
                args = patch_logger.call_args
                assert 'Add filter failed.' == args[0][1]
            get_cat_info_patch.assert_called_once_with(category_name=name)

    async def test_create_filter(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        plugin_name = 'filter'
        name = 'test'
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await self.async_mock(None)
            _rv2 = await self.async_mock({'count': 0, 'rows': []})
            _se1 = await self.async_mock(None)
            _se2 = await self.async_mock({})
        else:
            _rv1 = asyncio.ensure_future(self.async_mock(None))
            _rv2 = asyncio.ensure_future(self.async_mock({'count': 0, 'rows': []}))
            _se1 = asyncio.ensure_future(self.async_mock(None))
            _se2 = asyncio.ensure_future(self.async_mock({}))
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', side_effect=[_se1, _se2]) as get_cat_info_patch:
                with patch.object(apiutils, 'get_plugin_info', return_value={"config": {'plugin': {'description': 'Python 3.5 filter plugin', 'type': 'string', 'default': 'filter'}}, "type": "filter"}) as api_utils_patch:
                    with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=_rv2) as query_tbl_patch:
                        with patch.object(storage_client_mock, 'insert_into_tbl', return_value=_rv1) as insert_tbl_patch:
                            with patch.object(cf_mgr, 'create_category', return_value=_rv1) as create_cat_patch:
                                with patch.object(cf_mgr, 'update_configuration_item_bulk', return_value=_rv1) as update_cfg_bulk_patch:
                                    with patch.object(common._logger, 'warning') as patch_logger2:
                                        resp = await client.post('/fledge/filter'.format("bench"), data=json.dumps(
                                            {"name": name, "plugin": plugin_name, "filter_config": {}}))
                                        assert 200 == resp.status
                                        r = await resp.text()
                                        json_response = json.loads(r)
                                        assert {'filter': name, 'description': "Configuration of 'test' filter for plugin 'filter'", 'value': {}} == json_response
                                    assert 2 == patch_logger2.call_count
                                update_cfg_bulk_patch.assert_called_once_with(name, {})
                            create_cat_patch.assert_called_once_with(category_description="Configuration of 'test' filter for plugin 'filter'", category_name='test', category_value={'plugin': {'description': 'Python 3.5 filter plugin', 'type': 'string', 'default': 'filter'}}, keep_original_items=True)
                        args, kwargs = insert_tbl_patch.call_args_list[0]
                        assert 'filters' == args[0]
                        assert {"name": "test", "plugin": "filter"} == json.loads(args[1])
                        # insert_tbl_patch.assert_called_once_with('filters', '{"name": "test", "plugin": "filter"}')
                    args, kwargs = query_tbl_patch.call_args_list[0]
                    assert 'filters' == args[0]
                    assert {"where": {"column": "name", "condition": "=", "value": "test"}} == json.loads(args[1])
                    # query_tbl_patch.assert_called_once_with('filters', '{"where": {"column": "name", "condition": "=", "value": "test"}}')
                api_utils_patch.assert_called_once_with(plugin_name, dir='filter')
            assert 2 == get_cat_info_patch.call_count

    async def test_delete_filter(self, client):
        async def q_result(*args):
            table = args[0]
            payload = args[1]

            if table == 'filters':
                assert {"where": {"column": "name", "condition": "=", "value": filter_name}} == json.loads(payload)
                return {'count': 1, 'rows': [{'name': filter_name, 'plugin': 'python35'}]}

            if table == 'filter_users':
                assert {"where": {"column": "name", "condition": "=", "value": filter_name}} == json.loads(payload)
                return {'count': 0, 'rows': []}

            if table == 'asset_tracker':
                assert {"return": ["deprecated_ts"],
                        "where": {"column": "plugin", "condition": "=", "value": filter_name}} == json.loads(payload)
                return {'count': 1, 'rows': [{'deprecated_ts': ''}]}

        filter_name = "AssetFilter"
        delete_result = {'response': 'deleted', 'rows_affected': 1}
        update_result = {'rows_affected': 1, "response": "updated"}
        storage_client_mock = MagicMock(StorageClientAsync)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await self.async_mock(None)
            _rv2 = await self.async_mock(delete_result)
            _rv3 = await self.async_mock(update_result)
        else:
            _rv1 = asyncio.ensure_future(self.async_mock(None))
            _rv2 = asyncio.ensure_future(self.async_mock(delete_result))
            _rv3 = asyncio.ensure_future(self.async_mock(update_result))

        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                with patch.object(storage_client_mock, 'delete_from_tbl', return_value=_rv2) as delete_tbl_patch:
                    with patch.object(filters, '_delete_configuration_category', return_value=_rv1) as delete_cfg_patch:
                        with patch.object(storage_client_mock, 'update_tbl', return_value=_rv3) as update_tbl_patch:
                            resp = await client.delete('/fledge/filter/{}'.format(filter_name))
                            assert 200 == resp.status
                            r = await resp.text()
                            json_response = json.loads(r)
                            assert {'result': 'Filter AssetFilter deleted successfully.'} == json_response
                        args, kwargs = update_tbl_patch.call_args
                        assert 'asset_tracker' == args[0]
                    args, kwargs = delete_cfg_patch.call_args
                    assert filter_name == args[1]
                delete_tbl_patch.assert_called_once_with(
                    'filters', '{"where": {"column": "name", "condition": "=", "value": "AssetFilter"}}')

    async def test_delete_filter_value_error(self, client):
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        message = "No such filter '{}' found".format(filter_name)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await self.async_mock({'count': 0, 'rows': []})
        else:
            _rv = asyncio.ensure_future(self.async_mock({'count': 0, 'rows': []}))
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=_rv):
                resp = await client.delete('/fledge/filter/{}'.format(filter_name))
                assert 404 == resp.status
                assert message == resp.reason
                r = await resp.text()
                json_response = json.loads(r)
                assert message == json_response['message']

    async def test_delete_filter_type_error(self, client):
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        message = 'string indices must be integers'
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            rv1 = await self.async_mock("blah")
        else:
            rv1 = asyncio.ensure_future(self.async_mock("blah"))

        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=rv1):
                resp = await client.delete('/fledge/filter/{}'.format(filter_name))
                assert 400 == resp.status
                assert message in resp.reason
                r = await resp.text()
                json_response = json.loads(r)
                assert message in json_response['message']

    async def test_delete_filter_conflict_error(self, client):
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        message = ("The filter '{}' is currently being used within a pipeline. "
                   "To delete the filter, you must first remove it from the pipeline.").format(filter_name)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _se1 = await self.async_mock({'count': 1, 'rows': [{'name': filter_name, 'plugin': 'python35'}]})
            _se2 = await self.async_mock({'count': 0, 'rows': ["Random"]})
        else:
            _se1 = asyncio.ensure_future(self.async_mock({'count': 1, 'rows': [{'name': filter_name, 'plugin': 'python35'}]}))
            _se2 = asyncio.ensure_future(self.async_mock({'count': 0, 'rows': ["Random"]}))
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              side_effect=[_se1, _se2]):
                resp = await client.delete('/fledge/filter/{}'.format(filter_name))
                assert 409 == resp.status
                assert message == resp.reason
                r = await resp.text()
                json_response = json.loads(r)
                assert message == json_response['message']

    async def test_delete_filter_storage_error(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        filter_name = "AssetFilter"
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=StorageServerError(
                    None, None, error='something went wrong')) as get_cat_info_patch:
                with patch.object(_LOGGER, 'exception') as patch_logger:
                    resp = await client.delete('/fledge/filter/{}'.format(filter_name))
                    assert 500 == resp.status
                    assert "something went wrong" == resp.reason
                assert 1 == patch_logger.call_count
                patch_logger.assert_called_once_with('Delete {} filter, caught storage exception: {}'.format(
                    filter_name, 'something went wrong'))
            get_cat_info_patch.assert_called_once_with(
                'filters', '{"where": {"column": "name", "condition": "=", "value": "AssetFilter"}}')

    @pytest.mark.parametrize("payload, message", [
        ({}, "'pipeline key-value pair is required in the payload.'"),
        ({"foo": "bar"}, "'pipeline key-value pair is required in the payload.'"),
        ({"Pipeline": []}, "'pipeline key-value pair is required in the payload.'"),
        ({"pipeline": 1}, "pipeline must be either a list of filters or an empty list."),
        ({"pipeline": False}, "pipeline must be either a list of filters or an empty list."),
        ({"pipeline": ""}, "pipeline must be either a list of filters or an empty list."),
        ({"pipeline": "AssetFilter"}, "pipeline must be either a list of filters or an empty list."),
        ({"pipeline": {}}, "pipeline must be either a list of filters or an empty list."),
        ({"pipeline": ["F1", "F1"]}, "The filter name 'F1' cannot be duplicated in the pipeline."),
        ({"pipeline": ["F1", "f1", "F2", "F2"]}, "The filter name 'F2' cannot be duplicated in the pipeline."),
        ({"pipeline": ["F1", "f1", ["F2"], "F2"]}, "The filter name 'F2' cannot be duplicated in the pipeline."),
        ({"pipeline": ["F1", ["f1"], ["f1", "F3"]]}, "The filter name 'f1' cannot be duplicated in the pipeline."),
        ({"pipeline": [["F1", "f1"], ["f1", "F3"]]}, "The filter name 'f1' cannot be duplicated in the pipeline.")
    ])
    async def test_bad_update_filter_pipeline(self, client, payload, message):
        resp = await client.put('/fledge/filter/{}/pipeline'.format("bench"), data=json.dumps(payload))
        assert 400 == resp.status
        assert message == resp.reason
        result = await resp.text()
        json_response = json.loads(result)
        assert {"message": message} == json_response

    @pytest.mark.parametrize("request_param, param, val", [
        ('?append_filter=T', 'append_filter', 't'),
        ('?append_filter=1', 'append_filter', '1'),
        ('?append_filter=t', 'append_filter', 't'),
        ('?append_filter=F', 'append_filter', 'f'),
        ('?append_filter=0', 'append_filter', '0'),
        ('?append_filter=f', 'append_filter', 'f'),
        ('?allow_duplicates=T', 'allow_duplicates', 't'),
        ('?allow_duplicates=1', 'allow_duplicates', '1'),
        ('?allow_duplicates=t', 'allow_duplicates', 't'),
        ('?allow_duplicates=F', 'allow_duplicates', 'f'),
        ('?allow_duplicates=0', 'allow_duplicates', '0'),
        ('?allow_duplicates=f', 'allow_duplicates', 'f')
    ])
    async def test_add_filter_pipeline_bad_request_param_val(self, client, request_param, param, val):
        user = "bench"
        resp = await client.put('/fledge/filter/{}/pipeline{}'.format(user, request_param), data=json.dumps(
            {"pipeline": ["AssetFilter"]}))
        assert 404 == resp.status
        assert "Only 'true' and 'false' are allowed for {}. {} given.".format(param, val) == resp.reason

    async def test_add_filter_pipeline_value_error_1(self, client):
        user = "bench"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await self.async_mock(None)
        else:
            _rv = asyncio.ensure_future(self.async_mock(None))
        msg = "No such '{}' category found.".format(user)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv) as get_cat_info_patch:
                resp = await client.put('/fledge/filter/{}/pipeline'.format(user), data=json.dumps(
                    {"pipeline": ["AssetFilter"]}))
                assert 404 == resp.status
                assert msg == resp.reason
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_add_filter_pipeline_value_error_2(self, client):
        user = "bench"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await self.async_mock(None)
        else:
            _rv = asyncio.ensure_future(self.async_mock(None))
        msg = "No such '{}' category found.".format(user)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv) as get_cat_info_patch:
                resp = await client.put('/fledge/filter/{}/pipeline'.format(user), data=json.dumps(
                    {"pipeline": ["AssetFilter"]}))
                assert 404 == resp.status
                assert msg == resp.reason
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_add_filter_pipeline_value_error_3(self, client):
        cat_info = {'filter': {'description': 'Filter pipeline', 'type': 'JSON', 'default': '{"pipeline": []}', 'value': '{"pipeline":[]}'},
                    'plugin': {'description': 'Benchmark C south plugin', 'type': 'string', 'default': 'Benchmark', 'value': 'Benchmark'},
                    'asset': {'description': 'Asset name prefix', 'type': 'string', 'default': 'Random', 'value': 'Random'}}
        user = "bench"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await self.async_mock(cat_info)
            _rv2 = await self.async_mock({'count': 1, 'rows': []})
        else:
            _rv1 = asyncio.ensure_future(self.async_mock(cat_info))
            _rv2 = asyncio.ensure_future(self.async_mock({'count': 1, 'rows': []}))
        msg = "No such 'AssetFilter' filter found in filters table."
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv1) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=_rv2) as query_tbl_patch:
                    resp = await client.put('/fledge/filter/{}/pipeline'.format(user), data=json.dumps(
                        {"pipeline": ["AssetFilter"]}))
                    assert 404 == resp.status
                    assert msg == resp.reason
                query_tbl_patch.assert_called_once_with(
                    'filters', '{"where": {"column": "name", "condition": "=", "value": "AssetFilter"}}')
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_add_filter_pipeline_value_error_4(self, client):
        async def query_result(*f_args):
            table = f_args[0]
            payload = f_args[1]
            assert {"where": {"column": "name", "condition": "=", "value": filter_name}} == json.loads(payload)
            if table == 'filters':
                return {'count': 1, 'rows': [{'name': filter_name, 'plugin': 'python35'}]}
            return {'count': 0, 'rows': []}

        cat_info = {'filter': {'description': 'Filter pipeline', 'type': 'JSON', 'default': '{"pipeline": []}',
                               'value': '{"pipeline":[]}'},
                    'plugin': {'description': 'Benchmark C south plugin', 'type': 'string', 'default': 'Benchmark',
                               'value': 'Benchmark'},
                    'asset': {'description': 'Asset name prefix', 'type': 'string', 'default': 'Random',
                              'value': 'Random'}}
        user = "bench"
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await self.async_mock(cat_info)
            _rv3 = await self.async_mock(None)
        else:
            _rv1 = asyncio.ensure_future(self.async_mock(cat_info))
            _rv3 = asyncio.ensure_future(self.async_mock(None))
        msg = 'No detail found for user: {} and filter: filter'.format(user)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items',
                              return_value=_rv1) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=query_result):
                    with patch.object(cf_mgr, 'set_category_item_value_entry',
                                      return_value=_rv3) as set_cat_item_patch:
                        with patch.object(filters, '_delete_child_filters',
                                          return_value=_rv3) as _delete_child_patch:
                            with patch.object(filters, '_add_child_filters',
                                              return_value=_rv3) as _add_child_patch:
                                with patch.object(cf_mgr, 'get_category_item', return_value=_rv3
                                                  ) as get_cat_item_patch:
                                    resp = await client.put('/fledge/filter/{}/pipeline'.format(user),
                                                            data=json.dumps({"pipeline": [filter_name]}))
                                    assert 404 == resp.status
                                    assert msg == resp.reason
                                    r = await resp.text()
                                    json_response = json.loads(r)
                                    assert {'message': msg} == json_response
                                get_cat_item_patch.assert_called_once_with(user, 'filter')
                            args, kwargs = _add_child_patch.call_args
                            assert user == args[2]
                            assert [filter_name] == args[3]
                            assert {'old_list': []} == kwargs
                        args, kwargs = _delete_child_patch.call_args
                        assert user == args[2]
                        assert [filter_name] == args[3]
                        assert {'old_list': []} == kwargs
                    set_cat_item_patch.assert_called_once_with(user, 'filter', {'pipeline': [filter_name]})
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_add_filter_pipeline_conflict_error(self, client):
        async def query_result(*f_args):
            table = f_args[0]
            payload = f_args[1]
            assert {"where": {"column": "name", "condition": "=", "value": filter_name}} == json.loads(payload)
            if table == 'filters':
                return {'count': 1, 'rows': [{'name': filter_name, 'plugin': 'python35'}]}
            return {'count': 0, 'rows': [{'name': filter_name, 'user': 'S1'}]}

        cat_info = {'filter': {'description': 'Filter pipeline', 'type': 'JSON', 'default': '{"pipeline": []}',
                               'value': '{"pipeline":[]}'},
                    'plugin': {'description': 'Benchmark C south plugin', 'type': 'string', 'default': 'Benchmark',
                               'value': 'Benchmark'},
                    'asset': {'description': 'Asset name prefix', 'type': 'string', 'default': 'Random',
                              'value': 'Random'}}
        user = "bench"
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await self.async_mock(cat_info)
            _rv3 = await self.async_mock(None)
        else:
            _rv1 = asyncio.ensure_future(self.async_mock(cat_info))
            _rv3 = asyncio.ensure_future(self.async_mock(None))
        msg = ("The filter '{}' is currently in use. To update the filter pipeline, "
               "you must first remove it from the '{}' instance.").format(filter_name, 'S1')
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items',
                              return_value=_rv1) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=query_result):
                    resp = await client.put('/fledge/filter/{}/pipeline'.format(user),
                                            data=json.dumps({"pipeline": [filter_name]}))
                    assert 409 == resp.status
                    assert msg == resp.reason
                    r = await resp.text()
                    json_response = json.loads(r)
                    assert {'message': msg} == json_response

    async def test_add_filter_pipeline_storage_error(self, client):
        cat_info = {'filter': {'description': 'Filter pipeline', 'type': 'JSON', 'default': '{"pipeline": []}', 'value': '{"pipeline":[]}'},
                    'plugin': {'description': 'Benchmark C south plugin', 'type': 'string', 'default': 'Benchmark', 'value': 'Benchmark'},
                    'asset': {'description': 'Asset name prefix', 'type': 'string', 'default': 'Random', 'value': 'Random'}}
        user = "bench"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await self.async_mock(cat_info)
        else:
            _rv = asyncio.ensure_future(self.async_mock(cat_info))
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload',  side_effect=StorageServerError(None, None, error='something went wrong')):
                    with patch.object(_LOGGER, 'error') as patch_logger:
                        resp = await client.put('/fledge/filter/{}/pipeline'.format(user), data=json.dumps({"pipeline": ["AssetFilter"]}))
                        assert 500 == resp.status
                        assert "something went wrong" == resp.reason
                    assert 1 == patch_logger.call_count
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_add_filter_pipeline(self, client):
        async def query_result(*f_args):
            table = f_args[0]
            payload = f_args[1]
            assert {"where": {"column": "name", "condition": "=", "value": filter_name}} == json.loads(payload)
            if table == 'filters':
                return {'count': 1, 'rows': [{'name': filter_name, 'plugin': 'python35'}]}
            return {'count': 0, 'rows': []}

        cat_info = {'filter': {
            'description': 'Filter pipeline', 'type': 'JSON', 'default': '{"pipeline": []}',
            'value': '{"pipeline":[]}'}, 'plugin': {
            'description': 'Benchmark C south plugin', 'type': 'string', 'default': 'Benchmark', 'value': 'Benchmark'},
            'asset': {'description': 'Asset name prefix', 'type': 'string', 'default': 'Random', 'value': 'Random'}}
        update_filter_val = cat_info
        update_filter_val['filter']['value'] = '{"pipeline": ["AssetFilter"]}'
        user = "bench"
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        cat_child = {'children': ['Benchmark Filters', 'BenchmarkAdvanced', 'Benchmark_{}'.format(filter_name),
                                  filter_name]}
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await self.async_mock(cat_info)
            _rv3 = await self.async_mock(None)
            _rv4 = await self.async_mock(update_filter_val['filter'])
            _rv5 = await self.async_mock(cat_child)
        else:
            _rv1 = asyncio.ensure_future(self.async_mock(cat_info))
            _rv3 = asyncio.ensure_future(self.async_mock(None))
            _rv4 = asyncio.ensure_future(self.async_mock(update_filter_val['filter']))
            _rv5 = asyncio.ensure_future(self.async_mock(cat_child))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv1) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=query_result):
                    with patch.object(filters, '_delete_child_filters', return_value=_rv3
                                      ) as _delete_child_patch:
                        with patch.object(filters, '_add_child_filters', return_value=_rv3
                                          ) as _add_child_patch:
                            with patch.object(cf_mgr, 'set_category_item_value_entry',
                                              return_value=_rv3) as set_cat_item_patch:
                                with patch.object(cf_mgr, 'get_category_item', return_value=_rv4
                                                  ) as get_cat_item_patch:
                                    with patch.object(cf_mgr, 'create_child_category',
                                                      return_value=_rv5) as create_child_patch:
                                        resp = await client.put('/fledge/filter/{}/pipeline'.format(user),
                                                                data=json.dumps({"pipeline": [filter_name]}))
                                        assert 200 == resp.status
                                        r = await resp.text()
                                        json_response = json.loads(r)
                                        message = "Filter pipeline {'pipeline': ['AssetFilter']} updated successfully"
                                        assert {'result': message} == json_response
                                    create_child_patch.assert_called_once_with(user, [filter_name])
                                get_cat_item_patch.assert_called_once_with(user, 'filter')
                            set_cat_item_patch.assert_called_once_with(user, 'filter', {'pipeline': [filter_name]})
                        args, kwargs = _add_child_patch.call_args
                        assert user == args[2]
                        assert [filter_name] == args[3]
                        assert {'old_list': [filter_name]} == kwargs
                    args, kwargs = _delete_child_patch.call_args
                    assert user == args[2]
                    assert [filter_name] == args[3]
                    assert {'old_list': [filter_name]} == kwargs
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_add_filter_pipeline_without_filter_config(self, client):
        async def query_result(*f_args):
            table = f_args[0]
            payload = f_args[1]
            assert {"where": {"column": "name", "condition": "=", "value": filter_name}} == json.loads(payload)
            if table == 'filters':
                return {'count': 1, 'rows': [{'name': filter_name, 'plugin': 'python35'}]}
            return {'count': 0, 'rows': [{'name': filter_name, 'user': user}]}

        cat_info = {'plugin': {
            'description': 'Benchmark C south plugin', 'type': 'string', 'default': 'Benchmark', 'value': 'Benchmark'},
            'asset': {'description': 'Asset name prefix', 'type': 'string', 'default': 'Random', 'value': 'Random'}}
        user = "bench"
        filter_name = "AssetFilter"
        new_item_val = {'filter': {'description': 'Filter pipeline', 'type': 'JSON',
                                   'default': '{"pipeline": []}', 'value': '{"pipeline":[]}'}}
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        cat_child = {'children': ['Benchmark Filters', 'BenchmarkAdvanced', 'Benchmark_{}'.format(filter_name),
                                  filter_name]}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await self.async_mock(cat_info)
            _rv3 = await self.async_mock(None)
            _rv4 = await self.async_mock(new_item_val['filter'])
            _rv5 = await self.async_mock(cat_child)
        else:
            _rv1 = asyncio.ensure_future(self.async_mock(cat_info))
            _rv3 = asyncio.ensure_future(self.async_mock(None))
            _rv4 = asyncio.ensure_future(self.async_mock(new_item_val['filter']))
            _rv5 = asyncio.ensure_future(self.async_mock(cat_child))

        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv1) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=query_result):
                    with patch.object(cf_mgr, 'create_category', return_value=_rv3) as create_cat_patch:
                        with patch.object(filters, '_add_child_filters', return_value=_rv3) as _add_child_patch:
                            with patch.object(cf_mgr, 'get_category_item', return_value=_rv4) as get_cat_item_patch:
                                with patch.object(cf_mgr, 'create_child_category',
                                                  return_value=_rv5) as create_child_patch:
                                    resp = await client.put('/fledge/filter/{}/pipeline'.format(user),
                                                            data=json.dumps({"pipeline": [filter_name]}))
                                    assert 200 == resp.status
                                    r = await resp.text()
                                    json_response = json.loads(r)
                                    message = "Filter pipeline {'pipeline': []} updated successfully"
                                    assert {'result': message} == json_response
                                create_child_patch.assert_called_once_with(user, [filter_name])
                            get_cat_item_patch.assert_called_once_with(user, 'filter')
                        args, kwargs = _add_child_patch.call_args
                        assert user == args[2]
                        assert [filter_name] == args[3]
                    create_cat_patch.assert_called_once_with(category_name='bench', category_value={
                        'filter': {'description': 'Filter pipeline', 'readonly': 'true', 'type': 'JSON',
                                   'default': f'{{"pipeline": ["{filter_name}"]}}'}}, keep_original_items=True)
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_get_filter_pipeline(self, client):
        d = {'filter': {'description': 'Filter pipeline', 'type': 'JSON', 'default': '{"pipeline": ["AssetFilter"]}', 'value': '{"pipeline": ["AssetFilter"]}'},
             'plugin': {'description': 'CoAP Listener South Plugin', 'type': 'string', 'default': 'coap', 'value': 'coap'},
             'port': {'description': 'Port to listen on', 'type': 'integer', 'default': '5683', 'value': '5683'},
             'uri': {'description': 'URI to accept data on', 'type': 'string', 'default': 'sensor-values', 'value': 'sensor-values'},
             'management_host': {'description': 'Management host', 'type': 'string', 'default': '127.0.0.1', 'value': '127.0.0.1'}}
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        user = "Coap"
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await self.async_mock(d)
        else:
            _rv = asyncio.ensure_future(self.async_mock(d))
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv) as get_cat_info_patch:
                resp = await client.get('/fledge/filter/{}/pipeline'.format(user))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert {'result': {'pipeline': ['AssetFilter']}} == json_response
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_get_filter_pipeline_value_error(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        user = "Blah"
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await self.async_mock(None)
        else:
            _rv = asyncio.ensure_future(self.async_mock(None))
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv) as get_cat_info_patch:
                resp = await client.get('/fledge/filter/{}/pipeline'.format(user))
                assert 404 == resp.status
                assert "No such '{}' category found.".format(user) == resp.reason
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_get_filter_pipeline_key_error(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        user = "Blah"
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await self.async_mock({})
        else:
            _rv = asyncio.ensure_future(self.async_mock({}))
        msg = "No filter pipeline exists for {}.".format(user)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=_rv) as get_cat_info_patch:
                resp = await client.get('/fledge/filter/{}/pipeline'.format(user))
                assert 404 == resp.status
                assert msg == resp.reason
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_get_filter_pipeline_storage_error(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        user = "Random"
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', side_effect=StorageServerError(
                    None, None, error='something went wrong')) as get_cat_info_patch:
                with patch.object(_LOGGER, 'error') as patch_logger:
                    resp = await client.get('/fledge/filter/{}/pipeline'.format(user))
                    assert 500 == resp.status
                    assert "something went wrong" == resp.reason
                assert 1 == patch_logger.call_count
                patch_logger.assert_called_once_with(
                    'Failed to delete filter pipeline {}. Storage error occurred: {}'.format(
                        user, 'something went wrong'), exc_info=True)
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_get_filter_pipeline_exception(self, client):
        user = "Random"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', side_effect=Exception) as get_cat_info_patch:
                with patch.object(_LOGGER, 'error') as patch_logger:
                    resp = await client.get('/fledge/filter/{}/pipeline'.format(user))
                    assert 500 == resp.status
                    assert resp.reason is ''
                assert 1 == patch_logger.call_count
            get_cat_info_patch.assert_called_once_with(category_name=user)

    @pytest.mark.skip(reason='Incomplete')
    async def test_delete_filter_pipeline(self, client):
        user = "Random"
        resp = await client.delete('/fledge/filter/{}/pipeline'.format(user))
        assert 500 == resp.status

    async def test_delete_configuration_category(self, mocker):
        # GIVEN
        mock_payload = {
               'where': {
                 'column': 'key',
                 'condition': '=',
                 'value': 'test'
               }
        }
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = MagicMock(ConfigurationManager)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await asyncio.sleep(.1)
        else:
            _rv = asyncio.ensure_future(asyncio.sleep(.1))
        
        mock_connect = mocker.patch.object(connect, 'get_storage_async', return_value=storage_client_mock)
        delete_tbl_patch = mocker.patch.object(storage_client_mock, 'delete_from_tbl', return_value=_rv)
        cache_manager = mocker.patch.object(c_mgr, '_cacheManager')
        cache_remove = mocker.patch.object(cache_manager, 'remove', return_value=MagicMock())

        # WHEN
        await filters._delete_configuration_category(storage_client_mock, "test")

        # THEN
        args, kwargs = delete_tbl_patch.call_args
        assert 'configuration' == args[0]
        p = json.loads(args[1])
        assert mock_payload == p
        # TODO: cache_remove.assert_called_once_with("test")

    def test_diff(self):
        in_list1 = ['a', 'b', 'c']
        in_list2 = ['x', 'y', 'z']
        out_list = ['x', 'y', 'z']
        assert out_list == filters._diff(in_list1, in_list2)

    def test_delete_keys_from_dict(self):
        in_dict_del = {
            "assetName": {
                "order": "1",
                "description": "Name of Asset",
                "type": "string",
                "value": "sinusoid1",
                "default": "sinusoid",
                "displayName": "Asset name"
            },
            "plugin": {
                "description": "Sinusoid Plugin",
                "type": "string",
                "readonly": "true",
                "default": "sinusoid",
                "value": "sinusoid1"
            },
            "filter": {
                "description": "Filter pipeline",
                "type": "JSON",
                "default": "{\"pipeline\": [\"S1\"]}",
                "value": "{\"pipeline\": [\"S11\"]}"
            },
            "dataPointsPerSec": {
                "order": "2",
                "description": "Data points per second",
                "type": "integer",
                "value": "11",
                "default": "1",
                "displayName": "Data points per second"
            }
        }
        out_dict_del = {
            "assetName": {
                "order": "1",
                "description": "Name of Asset",
                "type": "string",
                "default": "sinusoid",
                "displayName": "Asset name"
            },
            "plugin": {
                "description": "Sinusoid Plugin",
                "type": "string",
                "readonly": "true",
                "default": "sinusoid",
            },
            "filter": {
                "description": "Filter pipeline",
                "type": "JSON",
                "default": "{\"pipeline\": [\"S1\"]}",
            },
            "dataPointsPerSec": {
                "order": "2",
                "description": "Data points per second",
                "type": "integer",
                "default": "1",
                "displayName": "Data points per second"
            }
        }
        lst_keys = ['value']
        deleted_values = {
            'plugin': 'sinusoid1',
            'assetName': 'sinusoid1',
            'filter': {
                'pipeline': ['S11']
            },
            'dataPointsPerSec': '11'
        }
        a, b = filters._delete_keys_from_dict(in_dict_del, lst_keys, deleted_values={}, parent=None)
        assert out_dict_del, deleted_values == (a, b)

    @pytest.mark.parametrize("list1, list2, diff", [
        (['Rename'], ['Exp #1', 'Rename'], ['Exp #1']),
        (['Meta_1'], ['Meta_1'], []),
        (['Meta_1', 'Exp#1'], ['Meta_1'], []),
        (['Exp'], ['Exp #1', 'Rename'], ['Exp #1', 'Rename']),
        (['Exp', 'Exp #1', 'Rename'], ['Exp #1', 'Rename'], []),
        ([['Rename #1'], 'Scale', 'Meta Data'], ['Asset'], ['Asset']),
        ([['RE2'], 'RE3', 'PY35'], [['RE2', 'RE3'], 'PY35'], []),
        ([['Py 35', 'Py#1 35'], 'Py35'], [['Py25', 'Py']], ['Py25', 'Py']),
        ([['Rms #1'], 'Scale', 'Meta Data'], [['Scale'], 'Meta Data'], [])
    ])
    async def test__diff(self, list1, list2, diff):
        assert diff == filters._diff(list1, list2)


    async def test_delete_child_filters(self, mocker):
        # GIVEN
        user_name_mock = 'random1'
        new_list_mock = ['scale2', 'python35b', 'meta2']
        old_list_mock = ['scale1', 'python35a', 'meta1']

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr_mock = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await self.async_mock(None)
            _rv2 = await self.async_mock({'count': 0, 'rows': []})
        else:
            _rv = asyncio.ensure_future(self.async_mock(None))
            _rv2 = asyncio.ensure_future(self.async_mock({'count': 0, 'rows': []}))

        mocker.patch.object(connect, 'get_storage_async', return_value=storage_client_mock)
        delete_child_category_mock = mocker.patch.object(c_mgr_mock, 'delete_child_category',
                                                         return_value=(await self.async_mock(None)))
        delete_tbl_patch = mocker.patch.object(storage_client_mock, 'delete_from_tbl', return_value=_rv)
        delete_configuration_category_mock = mocker.patch.object(filters, '_delete_configuration_category',
                                                                 return_value=_rv)

        get_filters_mock = mocker.patch.object(storage_client_mock, 'query_tbl_with_payload',
                                               return_value=_rv2)

        # WHEN
        await filters._delete_child_filters(storage_client_mock, c_mgr_mock, user_name_mock, new_list_mock,
                                            old_list_mock)

        # THEN
        calls = get_filters_mock.call_args_list
        args, kwargs = calls[0]
        assert 'filters' == args[0]
        p = json.loads(args[1])
        assert {"where": {"column": "name", "condition": "=", "value": "scale1"}} == p

        calls = delete_configuration_category_mock.call_args_list
        args, kwargs = calls[0]
        assert 'random1_scale1' == args[1]

        calls = delete_tbl_patch.call_args_list
        args, kwargs = calls[0]
        assert 'filter_users' == args[0]
        p = json.loads(args[1])
        assert {"where": {"column": "name", "condition": "=", "value": "scale1",
                          "and": {"column": "user", "condition": "=", "value": "random1"}}} == p

        args, kwargs = calls[1]
        assert 'filter_users' == args[0]
        p = json.loads(args[1])
        assert {"where": {"column": "name", "condition": "=", "value": "python35a",
                          "and": {"column": "user", "condition": "=", "value": "random1"}}} == p

        args, kwargs = calls[2]
        assert 'filter_users' == args[0]
        p = json.loads(args[1])
        assert {"where": {"column": "name", "condition": "=", "value": "meta1",
                          "and": {"column": "user", "condition": "=", "value": "random1"}}} == p

        calls_child = [call('random1', 'random1_scale1'),
                       call('random1', 'random1_python35a'),
                       call('random1', 'random1_meta1')]
        delete_child_category_mock.assert_has_calls(calls_child, any_order=True)

    async def test_add_child_filters(self, mocker):
        # GIVEN
        user_name_mock = 'random1'
        new_list_mock = ['scale1', 'meta2']
        old_list_mock = ['scale1', 'python35a']
        mock_cat = {
            "assetName": {
                "order": "1",
                "description": "Name of Asset",
                "type": "string",
                "value": "test1",
                "default": "test",
                "displayName": "Asset name"
            },
        }

        async def get_cat(category_name):
            category = category_name
            if category == "random1_scale1":
                return mock_cat
            if category == 'random1_meta2':
                return None
            if category == 'meta2':
                return mock_cat

        async def mock():
            return {}

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr_mock = MagicMock(ConfigurationManager)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await asyncio.sleep(.1)
            _rv2 = await mock()
        else:
            _rv = asyncio.ensure_future(asyncio.sleep(.1))
            _rv2 = asyncio.ensure_future(mock())

        connect_mock = mocker.patch.object(connect, 'get_storage_async', return_value=storage_client_mock)
        get_category_mock = mocker.patch.object(c_mgr_mock, 'get_category_all_items', side_effect=get_cat)
        create_category_mock = mocker.patch.object(c_mgr_mock, 'create_category', return_value=_rv2)
        create_child_category_mock = mocker.patch.object(c_mgr_mock, 'create_child_category', return_value=_rv2)
        update_config_bulk_mock = mocker.patch.object(c_mgr_mock, 'update_configuration_item_bulk', return_value=_rv)
        cache_manager = mocker.patch.object(c_mgr_mock, '_cacheManager')
        cache_remove = mocker.patch.object(cache_manager, 'remove', return_value=MagicMock())
        insert_tbl_patch = mocker.patch.object(storage_client_mock, 'insert_into_tbl', return_value=_rv)

        # WHEN
        await filters._add_child_filters(storage_client_mock, c_mgr_mock, user_name_mock, new_list_mock, old_list_mock)

        # THEN
        calls_get_cat = [call(category_name='random1_scale1'),
                         call(category_name='random1_meta2'),
                         call(category_name='meta2')]
        get_category_mock.assert_has_calls(calls_get_cat, any_order=True)

        calls_create_cat = [
            call(category_description='Configuration of meta2 filter for user random1', category_name='random1_meta2',
                 category_value={
                     'assetName': {'description': 'Name of Asset', 'type': 'string', 'order': '1', 'default': 'test',
                                   'displayName': 'Asset name'}}, keep_original_items=True)]
        create_category_mock.assert_has_calls(calls_create_cat, any_order=True)

        calls_create_child = [call(category_name='random1', children=['random1_scale1', 'random1_meta2'])]
        create_child_category_mock.assert_has_calls(calls_create_child, any_order=True)

        calls_update = [call('random1_meta2', {'assetName': 'test1'})]
        update_config_bulk_mock.assert_has_calls(calls_update, any_order=True)

        args, kwargs = insert_tbl_patch.call_args
        assert 'filter_users' == args[0]
        p = json.loads(args[1])
        assert {"user": "random1", "name": "meta2"} == p
