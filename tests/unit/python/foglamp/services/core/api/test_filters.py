# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import json
from unittest.mock import MagicMock, patch, call
from aiohttp import web
import pytest

from foglamp.services.core import routes
from foglamp.services.core import connect
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.common.storage_client.exceptions import StorageServerError
from foglamp.services.core.api import filters
from foglamp.services.core.api.filters import _LOGGER
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core.api import utils as apiutils

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "filters")
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
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=get_filters()) as query_tbl_patch:
                resp = await client.get('/foglamp/filter')
                assert 200 == resp.status
                result = await resp.text()
                json_response = json.loads(result)
                assert {'filters': []} == json_response
            query_tbl_patch.assert_called_once_with('filters')

    async def test_get_filters_storage_exception(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', side_effect=StorageServerError(None, None, error='something went wrong')) as query_tbl_patch:
                with patch.object(_LOGGER, 'exception') as log_exc:
                    resp = await client.get('/foglamp/filter')
                    assert 500 == resp.status
                    assert "something went wrong" == resp.reason
                assert 1 == log_exc.call_count
                log_exc.assert_called_once_with('Get filters, caught exception: %s', 'something went wrong')
            query_tbl_patch.assert_called_once_with('filters')

    async def test_get_filters_exception(self, client):
        async def get_filters():
            return {"count": 1}

        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=get_filters()) as query_tbl_patch:
                resp = await client.get('/foglamp/filter')
                assert 500 == resp.status
                assert "'rows'" == resp.reason
            query_tbl_patch.assert_called_once_with('filters')

    async def test_get_filter_by_name(self, client):
        @asyncio.coroutine
        def q_result(*args):
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
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(cat_info)) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                    resp = await client.get('/foglamp/filter/{}'.format(filter_name))
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
        filter_result = {'count': 1, 'rows': []}
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(cat_info)) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=self.async_mock(filter_result)) as query_tbl_with_payload_patch:
                    resp = await client.get('/foglamp/filter/{}'.format(filter_name))
                    assert 404 == resp.status
                    assert "No such filter '{}' found.".format(filter_name) == resp.reason
                query_tbl_with_payload_patch.assert_called_once_with('filters', '{"where": {"column": "name", "condition": "=", "value": "AssetFilter"}}')
            get_cat_info_patch.assert_called_once_with(filter_name)

    async def test_get_filter_by_name_value_error(self, client):
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as get_cat_info_patch:
                resp = await client.get('/foglamp/filter/{}'.format(filter_name))
                assert 404 == resp.status
                assert "No such 'AssetFilter' category found." == resp.reason
            get_cat_info_patch.assert_called_once_with(filter_name)

    async def test_get_filter_by_name_storage_error(self, client):
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', side_effect=StorageServerError(None, None, error='something went wrong')) as get_cat_info_patch:
                with patch.object(_LOGGER, 'exception') as log_exc:
                    resp = await client.get('/foglamp/filter/{}'.format(filter_name))
                    assert 500 == resp.status
                    assert "something went wrong" == resp.reason
                assert 1 == log_exc.call_count
                log_exc.assert_called_once_with('Get filter: %s, caught exception: %s', filter_name, 'something went wrong')
            get_cat_info_patch.assert_called_once_with(filter_name)

    async def test_get_filter_by_name_type_error(self, client):
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(0)) as get_cat_info_patch:
                resp = await client.get('/foglamp/filter/{}'.format(filter_name))
                assert 400 == resp.status
            get_cat_info_patch.assert_called_once_with(filter_name)

    async def test_get_filter_by_name_exception(self, client):
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', side_effect=Exception) as get_cat_info_patch:
                resp = await client.get('/foglamp/filter/{}'.format(filter_name))
                assert 500 == resp.status
                assert resp.reason is None
            get_cat_info_patch.assert_called_once_with(filter_name)

    @pytest.mark.parametrize("data", [
        {},
        {"name": "test"},
        {"plugin": "benchmark"},
        {"blah": "blah"}
    ])
    async def test_bad_create_filter(self, client, data):
        with patch.object(_LOGGER, 'exception') as log_exc:
            resp = await client.post('/foglamp/filter'.format("bench"), data=json.dumps(data))
            assert 400 == resp.status
            assert 'Filter name, plugin name are mandatory.' == resp.reason
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('Add filter, caught exception: Filter name, plugin name are mandatory.')

    async def test_create_filter_value_error_1(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock({"result": "test"})) as get_cat_info_patch:
                with patch.object(_LOGGER, 'exception') as log_exc:
                    resp = await client.post('/foglamp/filter'.format("bench"), data=json.dumps({"name": "test", "plugin": "benchmark"}))
                    assert 404 == resp.status
                    assert "This 'test' filter already exists" == resp.reason
                assert 1 == log_exc.call_count
                log_exc.assert_called_once_with("Add filter, caught exception: This 'test' filter already exists")
            get_cat_info_patch.assert_called_once_with(category_name='test')

    async def test_create_filter_value_error_2(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        plugin_name = 'benchmark'
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as get_cat_info_patch:
                with patch.object(apiutils, 'get_plugin_info', return_value=None) as api_utils_patch:
                    with patch.object(_LOGGER, 'exception') as log_exc:
                        resp = await client.post('/foglamp/filter'.format("bench"), data=json.dumps({"name": "test", "plugin": plugin_name}))
                        assert 404 == resp.status
                        assert "Can not get 'plugin_info' detail from plugin '{}'".format(plugin_name) == resp.reason
                    assert 1 == log_exc.call_count
                    log_exc.assert_called_once_with("Add filter, caught exception: Can not get 'plugin_info' detail from plugin '{}'".format(plugin_name))
                api_utils_patch.assert_called_once_with(plugin_name, dir='filter')
            get_cat_info_patch.assert_called_once_with(category_name='test')

    async def test_create_filter_value_error_3(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        plugin_name = 'benchmark'
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as get_cat_info_patch:
                with patch.object(apiutils, 'get_plugin_info', return_value={"config": {'plugin': {'description': 'Python 3.5 filter plugin', 'type': 'string', 'default': 'python35'}}, "type": "south"}) as api_utils_patch:
                    with patch.object(_LOGGER, 'exception') as log_exc:
                        resp = await client.post('/foglamp/filter'.format("bench"), data=json.dumps({"name": "test", "plugin": plugin_name}))
                        assert 404 == resp.status
                        assert "Loaded plugin 'python35', type 'south', doesn't match the specified one '{}', type 'filter'".format(plugin_name) == resp.reason
                    assert 1 == log_exc.call_count
                    log_exc.assert_called_once_with("Add filter, caught exception: Loaded plugin 'python35', type 'south', doesn't match the specified one '{}', type 'filter'".format(plugin_name))
                api_utils_patch.assert_called_once_with(plugin_name, dir='filter')
            get_cat_info_patch.assert_called_once_with(category_name='test')

    async def test_create_filter_value_error_4(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        plugin_name = 'filter'
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as get_cat_info_patch:
                with patch.object(apiutils, 'get_plugin_info', return_value={"config": {'plugin': {'description': 'Python 3.5 filter plugin', 'type': 'string', 'default': 'filter'}}, "type": "filter"}) as api_utils_patch:
                    with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=self.async_mock({'count': 0, 'rows': []})) as query_tbl_patch:
                        with patch.object(storage_client_mock, 'insert_into_tbl', return_value=self.async_mock(None)) as insert_tbl_patch:
                            with patch.object(cf_mgr, 'create_category', return_value=self.async_mock(None)) as create_cat_patch:
                                with patch.object(_LOGGER, 'exception') as log_exc:
                                    resp = await client.post('/foglamp/filter'.format("bench"), data=json.dumps({"name": "test", "plugin": plugin_name, "filter_config": "blah"}))
                                    assert 404 == resp.status
                                    assert "filter_config must be a JSON object" == resp.reason
                                assert 1 == log_exc.call_count
                                log_exc.assert_called_once_with("Add filter, caught exception: filter_config must be a JSON object")
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
            get_cat_info_patch.assert_called_once_with(category_name='test')

    async def test_create_filter_storage_error(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        plugin_name = 'filter'
        name = 'test'
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as get_cat_info_patch:
                with patch.object(apiutils, 'get_plugin_info', return_value={"config": {'plugin': {'description': 'Python 3.5 filter plugin', 'type': 'string', 'default': 'filter'}}, "type": "filter"}) as api_utils_patch:
                    with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=StorageServerError(None, None, error='something went wrong')):
                        with patch.object(filters, '_delete_configuration_category', return_value=self.async_mock(None)) as _delete_cfg_patch:
                            with patch.object(_LOGGER, 'exception') as log_exc:
                                resp = await client.post('/foglamp/filter'.format("bench"), data=json.dumps({"name": name, "plugin": plugin_name}))
                                assert 500 == resp.status
                                assert 'Failed to create filter.' == resp.reason
                            assert 1 == log_exc.call_count
                            log_exc.assert_called_once_with('Failed to create filter. %s', 'something went wrong')
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
                with patch.object(_LOGGER, 'exception') as log_exc:
                    resp = await client.post('/foglamp/filter'.format("bench"), data=json.dumps({"name": name, "plugin": plugin_name}))
                    assert 500 == resp.status
                    assert resp.reason is None
                assert 1 == log_exc.call_count
                log_exc.assert_called_once_with('Add filter, caught exception:  %s', '')
            get_cat_info_patch.assert_called_once_with(category_name=name)

    async def test_create_filter(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        plugin_name = 'filter'
        name = 'test'
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', side_effect=[self.async_mock(None), self.async_mock({})]) as get_cat_info_patch:
                with patch.object(apiutils, 'get_plugin_info', return_value={"config": {'plugin': {'description': 'Python 3.5 filter plugin', 'type': 'string', 'default': 'filter'}}, "type": "filter"}) as api_utils_patch:
                    with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=self.async_mock({'count': 0, 'rows': []})) as query_tbl_patch:
                        with patch.object(storage_client_mock, 'insert_into_tbl', return_value=self.async_mock(None)) as insert_tbl_patch:
                            with patch.object(cf_mgr, 'create_category', return_value=self.async_mock(None)) as create_cat_patch:
                                with patch.object(cf_mgr, 'update_configuration_item_bulk', return_value=self.async_mock(None)) as update_cfg_bulk_patch:
                                    resp = await client.post('/foglamp/filter'.format("bench"), data=json.dumps({"name": name, "plugin": plugin_name, "filter_config": {}}))
                                    assert 200 == resp.status
                                    r = await resp.text()
                                    json_response = json.loads(r)
                                    assert {'filter': name, 'description': "Configuration of 'test' filter for plugin 'filter'", 'value': {}} == json_response
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
        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            payload = args[1]

            if table == 'filters':
                assert {"where": {"column": "name", "condition": "=", "value": filter_name}} == json.loads(payload)
                return {'count': 1, 'rows': [{'name': filter_name, 'plugin': 'python35'}]}

            if table == 'filter_users':
                assert {"where": {"column": "name", "condition": "=", "value": filter_name}} == json.loads(payload)
                return {'count': 0, 'rows': []}

        filter_name = "AssetFilter"
        delete_result = {'response': 'deleted', 'rows_affected': 1}
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result):
                with patch.object(storage_client_mock, 'delete_from_tbl', return_value=self.async_mock(delete_result)) as delete_tbl_patch:
                    with patch.object(filters, '_delete_configuration_category', return_value=self.async_mock(None)) as delete_cfg_patch:
                        resp = await client.delete('/foglamp/filter/{}'.format(filter_name))
                        assert 200 == resp.status
                        r = await resp.text()
                        json_response = json.loads(r)
                        assert {'result': 'Filter AssetFilter deleted successfully'} == json_response
                    args, kwargs = delete_cfg_patch.call_args
                    assert filter_name == args[1]
                delete_tbl_patch.assert_called_once_with('filters', '{"where": {"column": "name", "condition": "=", "value": "AssetFilter"}}')

    async def test_delete_filter_value_error(self, client):
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=self.async_mock({'count': 0, 'rows': []})):
                resp = await client.delete('/foglamp/filter/{}'.format(filter_name))
                assert 404 == resp.status
                assert "No such filter '{}' found".format(filter_name) == resp.reason

    async def test_delete_filter_type_error(self, client):
        filter_name = "AssetFilter"
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              side_effect=[self.async_mock({'count': 1, 'rows': [{'name': filter_name, 'plugin': 'python35'}]}),
                                           self.async_mock({'count': 0, 'rows': ["Random"]})]):
                resp = await client.delete('/foglamp/filter/{}'.format(filter_name))
                assert 400 == resp.status
                assert "Filter 'AssetFilter' found in pipelines".format(filter_name) == resp.reason

    async def test_delete_filter_storage_error(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        filter_name = "AssetFilter"
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=StorageServerError(None, None, error='something went wrong')) as get_cat_info_patch:
                with patch.object(_LOGGER, 'exception') as log_exc:
                    resp = await client.delete('/foglamp/filter/{}'.format(filter_name))
                    assert 500 == resp.status
                    assert "something went wrong" == resp.reason
                assert 1 == log_exc.call_count
                log_exc.assert_called_once_with('Delete filter: %s, caught exception: %s', filter_name, 'something went wrong')
            get_cat_info_patch.assert_called_once_with('filters', '{"where": {"column": "name", "condition": "=", "value": "AssetFilter"}}')

    async def test_add_filter_pipeline_type_error(self, client):
        with patch.object(_LOGGER, 'exception') as log_exc:
            resp = await client.put('/foglamp/filter/{}/pipeline'.format("bench"), data=json.dumps({"pipeline": "AssetFilter"}))
            assert 400 == resp.status
            assert "Pipeline must be a list of filters or an empty value" == resp.reason
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('Add filters pipeline, caught exception: %s', 'Pipeline must be a list of filters or an empty value')

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
        with patch.object(_LOGGER, 'exception') as log_exc:
            resp = await client.put('/foglamp/filter/{}/pipeline{}'.format(user, request_param), data=json.dumps({"pipeline": ["AssetFilter"]}))
            assert 404 == resp.status
            assert "Only 'true' and 'false' are allowed for {}. {} given.".format(param, val) == resp.reason
        assert 1 == log_exc.call_count

    async def test_add_filter_pipeline_value_error_1(self, client):
        user = "bench"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as get_cat_info_patch:
                with patch.object(_LOGGER, 'exception') as log_exc:
                    resp = await client.put('/foglamp/filter/{}/pipeline'.format(user), data=json.dumps({"pipeline": ["AssetFilter"]}))
                    assert 404 == resp.status
                assert 1 == log_exc.call_count
                log_exc.assert_called_once_with('Add filters pipeline, caught exception: %s', "No such '{}' category found.".format(user))
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_add_filter_pipeline_value_error_2(self, client):
        user = "bench"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as get_cat_info_patch:
                with patch.object(_LOGGER, 'exception') as log_exc:
                    resp = await client.put('/foglamp/filter/{}/pipeline'.format(user), data=json.dumps({"pipeline": ["AssetFilter"]}))
                    assert 404 == resp.status
                assert 1 == log_exc.call_count
                log_exc.assert_called_once_with('Add filters pipeline, caught exception: %s', "No such '{}' category found.".format(user))
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_add_filter_pipeline_value_error_3(self, client):
        cat_info = {'filter': {'description': 'Filter pipeline', 'type': 'JSON', 'default': '{"pipeline": []}', 'value': '{"pipeline":[]}'},
                    'plugin': {'description': 'Benchmark C south plugin', 'type': 'string', 'default': 'Benchmark', 'value': 'Benchmark'},
                    'asset': {'description': 'Asset name prefix', 'type': 'string', 'default': 'Random', 'value': 'Random'}}
        user = "bench"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(cat_info)) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=self.async_mock({'count': 1, 'rows': []})) as query_tbl_patch:
                    with patch.object(_LOGGER, 'exception') as log_exc:
                        resp = await client.put('/foglamp/filter/{}/pipeline'.format(user), data=json.dumps({"pipeline": ["AssetFilter"]}))
                        assert 404 == resp.status
                        assert "No such 'AssetFilter' filter found in filters table." == resp.reason
                    assert 1 == log_exc.call_count
                    log_exc.assert_called_once_with('Add filters pipeline, caught exception: %s', "No such 'AssetFilter' filter found in filters table.")
                query_tbl_patch.assert_called_once_with('filters', '{"where": {"column": "name", "condition": "=", "value": "AssetFilter"}}')
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_add_filter_pipeline_value_error_4(self, client):
        cat_info = {'filter': {'description': 'Filter pipeline', 'type': 'JSON', 'default': '{"pipeline": []}',
                               'value': '{"pipeline":[]}'},
                    'plugin': {'description': 'Benchmark C south plugin', 'type': 'string', 'default': 'Benchmark',
                               'value': 'Benchmark'},
                    'asset': {'description': 'Asset name prefix', 'type': 'string', 'default': 'Random',
                              'value': 'Random'}}
        query_tbl_payload_res = {'count': 1, 'rows': [{'name': 'AssetFilter2', 'plugin': 'python35'}]}
        user = "bench"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items',
                              return_value=self.async_mock(cat_info)) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                  return_value=self.async_mock(query_tbl_payload_res)) as query_tbl_patch:
                    with patch.object(cf_mgr, 'set_category_item_value_entry',
                                      return_value=self.async_mock(None)) as set_cat_item_patch:
                        with patch.object(filters, '_delete_child_filters',
                                          return_value=self.async_mock(None)) as _delete_child_patch:
                            with patch.object(filters, '_add_child_filters',
                                              return_value=self.async_mock(None)) as _add_child_patch:
                                with patch.object(cf_mgr, 'get_category_item', return_value=self.async_mock(None)) as get_cat_item_patch:
                                    with patch.object(_LOGGER, 'exception') as log_exc:
                                        resp = await client.put('/foglamp/filter/{}/pipeline'.format(user),
                                                                data=json.dumps({"pipeline": ["AssetFilter"]}))
                                        assert 404 == resp.status
                                        assert 'No detail found for user: {} and filter: filter'.format(user) == resp.reason
                                    assert 1 == log_exc.call_count
                                    log_exc.assert_called_once_with('Add filters pipeline, caught exception: %s', 'No detail found for user: bench and filter: filter')
                                get_cat_item_patch.assert_called_once_with(user, 'filter')
                            args, kwargs = _add_child_patch.call_args
                            assert user == args[2]
                            assert ['AssetFilter'] == args[3]
                            assert {'old_list': []} == kwargs
                        args, kwargs = _delete_child_patch.call_args
                        assert user == args[2]
                        assert ['AssetFilter'] == args[3]
                        assert {'old_list': []} == kwargs
                    set_cat_item_patch.assert_called_once_with(user, 'filter', {'pipeline': ['AssetFilter']})
                query_tbl_patch.assert_called_once_with('filters', '{"where": {"column": "name", "condition": "=", "value": "AssetFilter"}}')
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_add_filter_pipeline_storage_error(self, client):
        cat_info = {'filter': {'description': 'Filter pipeline', 'type': 'JSON', 'default': '{"pipeline": []}', 'value': '{"pipeline":[]}'},
                    'plugin': {'description': 'Benchmark C south plugin', 'type': 'string', 'default': 'Benchmark', 'value': 'Benchmark'},
                    'asset': {'description': 'Asset name prefix', 'type': 'string', 'default': 'Random', 'value': 'Random'}}
        user = "bench"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(cat_info)) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload',  side_effect=StorageServerError(None, None, error='something went wrong')):
                    with patch.object(_LOGGER, 'exception') as log_exc:
                        resp = await client.put('/foglamp/filter/{}/pipeline'.format(user), data=json.dumps({"pipeline": ["AssetFilter"]}))
                        assert 500 == resp.status
                        assert "something went wrong" == resp.reason
                    assert 1 == log_exc.call_count
                    log_exc.assert_called_once_with('Add filters pipeline, caught exception: %s', 'something went wrong')
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_add_filter_pipeline(self, client):
        cat_info = {'filter': {'description': 'Filter pipeline', 'type': 'JSON', 'default': '{"pipeline": []}', 'value': '{"pipeline":[]}'},
                    'plugin': {'description': 'Benchmark C south plugin', 'type': 'string', 'default': 'Benchmark', 'value': 'Benchmark'},
                    'asset': {'description': 'Asset name prefix', 'type': 'string', 'default': 'Random', 'value': 'Random'}}
        query_tbl_payload_res = {'count': 1, 'rows': [{'name': 'AssetFilter2', 'plugin': 'python35'}]}
        update_filter_val = cat_info
        update_filter_val['filter']['value'] = '{"pipeline": ["AssetFilter"]}'
        user = "bench"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(cat_info)) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=self.async_mock(query_tbl_payload_res)) as query_tbl_patch:
                    with patch.object(filters, '_delete_child_filters', return_value=self.async_mock(None)) as _delete_child_patch:
                        with patch.object(filters, '_add_child_filters', return_value=self.async_mock(None)) as _add_child_patch:
                            with patch.object(cf_mgr, 'set_category_item_value_entry', return_value=self.async_mock(None)) as set_cat_item_patch:
                                with patch.object(cf_mgr, 'get_category_item', return_value=self.async_mock(update_filter_val['filter'])) as get_cat_item_patch:
                                    resp = await client.put('/foglamp/filter/{}/pipeline'.format(user), data=json.dumps({"pipeline": ["AssetFilter"]}))
                                    assert 200 == resp.status
                                    r = await resp.text()
                                    json_response = json.loads(r)
                                    assert {'result': "Filter pipeline {'pipeline': ['AssetFilter']} updated successfully"} == json_response
                                get_cat_item_patch.assert_called_once_with(user, 'filter')
                            set_cat_item_patch.assert_called_once_with(user, 'filter', {'pipeline': ['AssetFilter']})
                        args, kwargs = _add_child_patch.call_args
                        assert user == args[2]
                        assert ['AssetFilter'] == args[3]
                        assert {'old_list': ['AssetFilter']} == kwargs
                    args, kwargs = _delete_child_patch.call_args
                    assert user == args[2]
                    assert ['AssetFilter'] == args[3]
                    assert {'old_list': ['AssetFilter']} == kwargs
                query_tbl_patch.assert_called_once_with('filters', '{"where": {"column": "name", "condition": "=", "value": "AssetFilter"}}')
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_add_filter_pipeline_without_filter_config(self, client):
        cat_info = {'plugin': {'description': 'Benchmark C south plugin', 'type': 'string', 'default': 'Benchmark', 'value': 'Benchmark'},
                    'asset': {'description': 'Asset name prefix', 'type': 'string', 'default': 'Random', 'value': 'Random'}}
        query_tbl_payload_res = {'count': 1, 'rows': [{'name': 'AssetFilter2', 'plugin': 'python35'}]}
        user = "bench"
        new_item_val = {'filter': {'description': 'Filter pipeline', 'type': 'JSON', 'default': '{"pipeline": []}', 'value': '{"pipeline":[]}'}}
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(cat_info)) as get_cat_info_patch:
                with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=self.async_mock(query_tbl_payload_res)) as query_tbl_patch:
                    with patch.object(cf_mgr, 'create_category', return_value=self.async_mock(None)) as create_cat_patch:
                        with patch.object(filters, '_add_child_filters', return_value=self.async_mock(None)) as _add_child_patch:
                            with patch.object(cf_mgr, 'get_category_item', return_value=self.async_mock(new_item_val['filter'])) as get_cat_item_patch:
                                resp = await client.put('/foglamp/filter/{}/pipeline'.format(user), data=json.dumps({"pipeline": ["AssetFilter"]}))
                                assert 200 == resp.status
                                r = await resp.text()
                                json_response = json.loads(r)
                                assert {'result': "Filter pipeline {'pipeline': []} updated successfully"} == json_response
                            get_cat_item_patch.assert_called_once_with(user, 'filter')
                        args, kwargs = _add_child_patch.call_args
                        assert user == args[2]
                        assert ['AssetFilter'] == args[3]
                    create_cat_patch.assert_called_once_with(category_name='bench', category_value={'filter': {'description': 'Filter pipeline', 'readonly' : 'true', 'type': 'JSON', 'default': '{"pipeline": ["AssetFilter"]}'}}, keep_original_items=True)
                query_tbl_patch.assert_called_once_with('filters', '{"where": {"column": "name", "condition": "=", "value": "AssetFilter"}}')
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
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(d)) as get_cat_info_patch:
                resp = await client.get('/foglamp/filter/{}/pipeline'.format(user))
                assert 200 == resp.status
                r = await resp.text()
                json_response = json.loads(r)
                assert {'result': {'pipeline': ['AssetFilter']}} == json_response
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_get_filter_pipeline_value_error(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        user = "Blah"
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock(None)) as get_cat_info_patch:
                resp = await client.get('/foglamp/filter/{}/pipeline'.format(user))
                assert 404 == resp.status
                assert "No such '{}' category found.".format(user) == resp.reason
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_get_filter_pipeline_key_error(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        user = "Blah"
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', return_value=self.async_mock({})) as get_cat_info_patch:
                with patch.object(_LOGGER, 'info') as log_exc:
                    resp = await client.get('/foglamp/filter/{}/pipeline'.format(user))
                    assert 404 == resp.status
                    assert "No filter pipeline exists for {}".format(user) == resp.reason
                assert 1 == log_exc.call_count
                log_exc.assert_called_once_with('No filter pipeline exists for {}'.format(user))
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_get_filter_pipeline_storage_error(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        user = "Random"
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', side_effect=StorageServerError(None, None, error='something went wrong')) as get_cat_info_patch:
                with patch.object(_LOGGER, 'exception') as log_exc:
                    resp = await client.get('/foglamp/filter/{}/pipeline'.format(user))
                    assert 500 == resp.status
                    assert "something went wrong" == resp.reason
                assert 1 == log_exc.call_count
                log_exc.assert_called_once_with('Get pipeline: %s, caught exception: %s', user, 'something went wrong')
            get_cat_info_patch.assert_called_once_with(category_name=user)

    async def test_get_filter_pipeline_exception(self, client):
        user = "Random"
        storage_client_mock = MagicMock(StorageClientAsync)
        cf_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(cf_mgr, 'get_category_all_items', side_effect=Exception) as get_cat_info_patch:
                resp = await client.get('/foglamp/filter/{}/pipeline'.format(user))
                assert 500 == resp.status
                assert resp.reason is None
            get_cat_info_patch.assert_called_once_with(category_name=user)

    @pytest.mark.skip(reason='Incomplete')
    async def test_delete_filter_pipeline(self, client):
        user = "Random"
        resp = await client.delete('/foglamp/filter/{}/pipeline'.format(user))
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

        mock_connect = mocker.patch.object(connect, 'get_storage_async', return_value=storage_client_mock)
        delete_tbl_patch = mocker.patch.object(storage_client_mock, 'delete_from_tbl', return_value=asyncio.sleep(.1))
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

    async def test_delete_child_filters(self, mocker):
        # GIVEN
        user_name_mock = 'random1'
        new_list_mock = ['scale2', 'python35b', 'meta2']
        old_list_mock = ['scale1', 'python35a', 'meta1']
        mock_payload = {"where": {"column": "name", "condition": "=", "value": "meta1", "and": {"column": "user", "condition": "=", "value": "random1"}}}

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr_mock = MagicMock(ConfigurationManager)

        connect_mock = mocker.patch.object(connect, 'get_storage_async', return_value=storage_client_mock)
        delete_child_category_mock = mocker.patch.object(c_mgr_mock, 'delete_child_category', return_value=asyncio.sleep(.1))
        delete_tbl_patch = mocker.patch.object(storage_client_mock, 'delete_from_tbl', return_value=asyncio.sleep(.1))
        delete_configuration_category_mock = mocker.patch.object(filters, '_delete_configuration_category', return_value=asyncio.sleep(.1))

        # WHEN
        await filters._delete_child_filters(storage_client_mock, c_mgr_mock, user_name_mock, new_list_mock, old_list_mock)

        # THEN
        args, kwargs = delete_tbl_patch.call_args
        assert 'filter_users' == args[0]
        p = json.loads(args[1])
        assert mock_payload == p

        calls = delete_tbl_patch.call_args_list
        args, kwargs = calls[0]
        assert 'filter_users' == args[0]
        p = json.loads(args[1])
        assert {"where": {"column": "name", "condition": "=", "value": "scale1", "and": {"column": "user", "condition": "=", "value": "random1"}}} == p

        args, kwargs = calls[1]
        assert 'filter_users' == args[0]
        p = json.loads(args[1])
        assert {"where": {"column": "name", "condition": "=", "value": "python35a", "and": {"column": "user", "condition": "=", "value": "random1"}}} == p

        args, kwargs = calls[2]
        assert 'filter_users' == args[0]
        p = json.loads(args[1])
        assert {"where": {"column": "name", "condition": "=", "value": "meta1", "and": {"column": "user", "condition": "=", "value": "random1"}}} == p

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

        @asyncio.coroutine
        def get_cat(category_name):
            category = category_name
            if category == "random1_scale1":
                return mock_cat
            if category == 'random1_meta2':
                return None
            if category == 'meta2':
                return mock_cat

        @asyncio.coroutine
        def create_cat():
            return {}

        @asyncio.coroutine
        def create_child_cat():
            return {}

        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr_mock = MagicMock(ConfigurationManager)

        connect_mock = mocker.patch.object(connect, 'get_storage_async', return_value=storage_client_mock)
        get_category_mock = mocker.patch.object(c_mgr_mock, 'get_category_all_items', side_effect=get_cat)
        create_category_mock = mocker.patch.object(c_mgr_mock, 'create_category', return_value=create_cat())
        create_child_category_mock = mocker.patch.object(c_mgr_mock, 'create_child_category',
                                                         return_value=create_child_cat())
        update_config_bulk_mock = mocker.patch.object(c_mgr_mock, 'update_configuration_item_bulk',
                                                      return_value=asyncio.sleep(.1))
        cache_manager = mocker.patch.object(c_mgr_mock, '_cacheManager')
        cache_remove = mocker.patch.object(cache_manager, 'remove', return_value=MagicMock())
        insert_tbl_patch = mocker.patch.object(storage_client_mock, 'insert_into_tbl', return_value=asyncio.sleep(.1))

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
