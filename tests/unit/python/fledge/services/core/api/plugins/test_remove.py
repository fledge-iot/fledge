# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
from unittest.mock import patch, MagicMock
import pytest
import sys
import asyncio

from aiohttp import web

from fledge.common.plugin_discovery import PluginDiscovery
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.services.core import connect, routes
from fledge.services.core.api import common
from fledge.services.core.api.plugins import remove as plugins_remove
from fledge.services.core.api.plugins.exceptions import *


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2020 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("api", "plugins", "remove")
class TestPluginRemove:
    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    RUN_TESTS_BEFORE_210_VERSION = False if common.get_version() <= "2.1.0" else True

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    @pytest.mark.parametrize("_type", ["blah", 1, "notificationDelivery", "notificationRule"])
    async def test_bad_type_plugin(self, client, _type):
        resp = await client.delete('/fledge/plugins/{}/name'.format(_type), data=None)
        assert 400 == resp.status
        assert "Invalid plugin type. Please provide valid type: ['north', 'south', 'filter', 'notify', 'rule']" == \
               resp.reason

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    @pytest.mark.parametrize("name", ["OMF", "omf", "Omf"])
    async def test_bad_update_of_inbuilt_plugin(self, client, name):
        resp = await client.delete('/fledge/plugins/north/{}'.format(name), data=None)
        assert 400 == resp.status
        assert "Cannot delete an inbuilt OMF plugin." == resp.reason

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    @pytest.mark.parametrize("name", ["http-south", "random"])
    async def test_bad_name_plugin(self, client, name):
        plugin_installed = [{"name": "sinusoid", "type": "south", "description": "Sinusoid Poll Plugin",
                             "version": "1.8.1", "installedDirectory": "south/sinusoid",
                             "packageName": "fledge-south-sinusoid"},
                            {"name": "http_south", "type": "south", "description": "HTTP Listener South Plugin",
                             "version": "1.8.1", "installedDirectory": "south/http_south",
                             "packageName": "fledge-south-http-south"},
                            {"name": "Random", "type": "south", "description": "Random data generation plugin",
                             "version": "1.8.1", "installedDirectory": "south/Random",
                             "packageName": "fledge-south-random"}
                            ]
        with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=plugin_installed
                          ) as plugin_installed_patch:
            resp = await client.delete('/fledge/plugins/south/{}'.format(name), data=None)
            assert 404 == resp.status
            expected_msg = "'Invalid plugin name {} or plugin is not installed.'".format(name)
            assert expected_msg == resp.reason
            result = await resp.text()
            response = json.loads(result)
            assert {'message': expected_msg} == response
        plugin_installed_patch.assert_called_once_with('south', False)

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    async def test_plugin_in_use(self, client):
        async def async_mock(return_value):
            return return_value

        name = "sinusoid"
        _type = "south"
        svc_list = ['Sine1', 'S2']
        plugin_installed = [{"name": name, "type": _type, "description": "Sinusoid Poll Plugin",
                             "version": "1.8.1", "installedDirectory": "{}/{}".format(_type, name),
                             "packageName": "fledge-{}-{}".format(_type, name)},
                            {"name": "http_south", "type": _type, "description": "HTTP Listener South Plugin",
                             "version": "1.8.1", "installedDirectory": "{}/http_south".format(_type),
                             "packageName": "fledge-{}-http-south".format(_type)}
                            ]
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock([{'service_list': svc_list}])
        else:
            _rv = asyncio.ensure_future(async_mock([{'service_list': svc_list}]))
        
        with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=plugin_installed
                          ) as plugin_installed_patch:
            with patch.object(plugins_remove, '_check_plugin_usage', return_value=_rv) as plugin_usage_patch:
                with patch.object(plugins_remove._logger, "warning") as patch_logger:
                    resp = await client.delete('/fledge/plugins/{}/{}'.format(_type, name), data=None)
                    assert 400 == resp.status
                    expected_msg = "{} cannot be removed. This is being used by {} instances.".format(name, svc_list)
                    assert expected_msg == resp.reason
                    result = await resp.text()
                    response = json.loads(result)
                    assert {'message': expected_msg} == response
                assert 1 == patch_logger.call_count
                patch_logger.assert_called_once_with(expected_msg)
            plugin_usage_patch.assert_called_once_with(_type, name)
        plugin_installed_patch.assert_called_once_with(_type, False)

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    async def test_notify_plugin_in_use(self, client):
        async def async_mock(return_value):
            return return_value

        notify_instances_list = ['N1', 'My Notify']
        plugin_type = "rule"
        plugin_type_installed_dir = "notificationRule"
        plugin_installed_dirname = "OutOfBound"
        pkg_name = "fledge-{}-outofbound".format(plugin_type)
        plugin_installed = [{"name": plugin_installed_dirname, "type": plugin_type,
                             "description": "Generate a notification if the values exceeds a configured value",
                             "version": "1.8.1", "installedDirectory": "{}/{}".format(plugin_type_installed_dir,
                                                                                      plugin_installed_dirname),
                             "packageName": pkg_name}]
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(notify_instances_list)
        else:
            _rv = asyncio.ensure_future(async_mock(notify_instances_list))
        
        with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=plugin_installed
                          ) as plugin_installed_patch:
            with patch.object(plugins_remove, '_check_plugin_usage_in_notification_instances', return_value=_rv) as plugin_usage_patch:
                with patch.object(plugins_remove._logger, "warning") as patch_logger:
                    resp = await client.delete('/fledge/plugins/{}/{}'.format(plugin_type, plugin_installed_dirname),
                                               data=None)
                    assert 400 == resp.status
                    expected_msg = "{} cannot be removed. This is being used by {} instances.".format(
                        plugin_installed_dirname, notify_instances_list)
                    assert expected_msg == resp.reason
                    result = await resp.text()
                    response = json.loads(result)
                    assert {'message': expected_msg} == response
                assert 1 == patch_logger.call_count
                patch_logger.assert_called_once_with(expected_msg)
            plugin_usage_patch.assert_called_once_with(plugin_installed_dirname)
        plugin_installed_patch.assert_called_once_with(plugin_type, False)

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    async def test_package_already_in_progress(self, client):
        async def async_mock(return_value):
            return return_value

        _type = "south"
        name = 'http_south'
        pkg_name = "fledge-south-http"
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "purge",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        select_row_resp = {'count': 1, 'rows': [{
            "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
            "name": pkg_name,
            "action": "purge",
            "status": -1,
            "log_file_uri": ""
        }]}
        expected_msg = '{} package purge already in progress.'.format(pkg_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        plugin_installed = [{"name": "sinusoid", "type": _type, "description": "Sinusoid Poll Plugin",
                             "version": "1.8.1", "installedDirectory": "{}/{}".format(_type, name),
                             "packageName": "fledge-{}-sinusoid".format(_type)},
                            {"name": name, "type": _type, "description": "HTTP Listener South Plugin",
                             "version": "1.8.1", "installedDirectory": "{}/{}".format(_type, name),
                             "packageName": pkg_name}
                            ]
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock([])
            _rv2 = await async_mock(select_row_resp)
        else:
            _rv1 = asyncio.ensure_future(async_mock([]))
            _rv2 = asyncio.ensure_future(async_mock(select_row_resp))
        
        with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=plugin_installed
                          ) as plugin_installed_patch:
            with patch.object(plugins_remove, '_check_plugin_usage', return_value=_rv1) as plugin_usage_patch:
                with patch.object(plugins_remove._logger, "info") as log_info_patch:
                    with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                        with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                          return_value=_rv2) as query_tbl_patch:
                            resp = await client.delete('/fledge/plugins/{}/{}'.format(_type, name), data=None)
                            assert 429 == resp.status
                            assert expected_msg == resp.reason
                            r = await resp.text()
                            actual = json.loads(r)
                            assert {'message': expected_msg} == actual
                        args, kwargs = query_tbl_patch.call_args_list[0]
                        assert 'packages' == args[0]
                        assert payload == json.loads(args[1])
                assert 1 == log_info_patch.call_count
                log_info_patch.assert_called_once_with(
                    'No entry found for http_south plugin in asset tracker; '
                    'or {} plugin may have been added in disabled state & never used.'.format(name))
            plugin_usage_patch.assert_called_once_with(_type, name)
        plugin_installed_patch.assert_called_once_with(_type, False)

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    async def test_package_when_not_in_use(self, client):
        
        async def async_mock(return_value):
            return return_value
        
        _type = "south"
        name = 'http_south'
        pkg_name = "fledge-south-http"
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "purge",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        select_row_resp = {'count': 1, 'rows': [{
            "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
            "name": pkg_name,
            "action": "purge",
            "status": 127,
            "log_file_uri": ""
        }]}
        insert = {"response": "inserted", "rows_affected": 1}
        insert_row = {'count': 1, 'rows': [{
                "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
                "name": pkg_name,
                "action": "purge",
                "status": -1,
                "log_file_uri": ""
            }]}
        delete = {"response": "deleted", "rows_affected": 1}
        delete_payload = {"where": {"column": "action", "condition": "=", "value": "purge",
                                    "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        storage_client_mock = MagicMock(StorageClientAsync)
        plugin_installed = [{"name": "sinusoid", "type": _type, "description": "Sinusoid Poll Plugin",
                             "version": "1.8.1", "installedDirectory": "{}/{}".format(_type, name),
                             "packageName": "fledge-{}-sinusoid".format(_type)},
                            {"name": name, "type": _type, "description": "HTTP Listener South Plugin",
                             "version": "1.8.1", "installedDirectory": "{}/{}".format(_type, name),
                             "packageName": pkg_name}
                            ]
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock([])
            _rv2 = await async_mock(delete)
            _rv3 = await async_mock(insert)
            _se1 = await async_mock(select_row_resp)
            _se2 = await async_mock(insert_row)
        else:
            _rv1 = asyncio.ensure_future(async_mock([]))
            _rv2 = asyncio.ensure_future(async_mock(delete))
            _rv3 = asyncio.ensure_future(async_mock(insert))
            _se1 = asyncio.ensure_future(async_mock(select_row_resp))
            _se2 = asyncio.ensure_future(async_mock(insert_row))
        
        with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=plugin_installed
                          ) as plugin_installed_patch:
            with patch.object(plugins_remove, '_check_plugin_usage', return_value=_rv1) as plugin_usage_patch:
                with patch.object(plugins_remove._logger, "info") as log_info_patch:
                    with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                        with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                          side_effect=[_se1, _se2]) as query_tbl_patch:
                            with patch.object(storage_client_mock, 'delete_from_tbl',
                                              return_value=_rv2) as delete_tbl_patch:
                                with patch.object(storage_client_mock, 'insert_into_tbl',
                                                  return_value=_rv3) as insert_tbl_patch:
                                    with patch('multiprocessing.Process'):
                                        resp = await client.delete('/fledge/plugins/{}/{}'.format(_type, name),
                                                                   data=None)
                                        assert 200 == resp.status
                                        result = await resp.text()
                                        response = json.loads(result)
                                        assert 'id' in response
                                        assert '{} plugin remove started.'.format(name) == response['message']
                                        assert response['statusLink'].startswith('fledge/package/purge/status?id=')
                                args, kwargs = insert_tbl_patch.call_args_list[0]
                                assert 'packages' == args[0]
                                actual = json.loads(args[1])
                                assert 'id' in actual
                                assert pkg_name == actual['name']
                                assert 'purge' == actual['action']
                                assert -1 == actual['status']
                                assert '' == actual['log_file_uri']
                            args, kwargs = delete_tbl_patch.call_args_list[0]
                            assert 'packages' == args[0]
                            assert delete_payload == json.loads(args[1])
                        args, kwargs = query_tbl_patch.call_args_list[0]
                        assert 'packages' == args[0]
                        assert payload == json.loads(args[1])
                assert 1 == log_info_patch.call_count
                log_info_patch.assert_called_once_with(
                    'No entry found for http_south plugin in asset tracker; '
                    'or {} plugin may have been added in disabled state & never used.'.format(name))
            plugin_usage_patch.assert_called_once_with(_type, name)
        plugin_installed_patch.assert_called_once_with(_type, False)
