# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
import uuid
from unittest.mock import patch, MagicMock
import pytest
import sys
import asyncio

from aiohttp import web

from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.plugin_discovery import PluginDiscovery
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.services.core import connect, routes, server
from fledge.services.core.api import common
from fledge.services.core.api.plugins import update as plugins_update
from fledge.services.core.api.plugins.exceptions import *
from fledge.services.core.scheduler.scheduler import Scheduler


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2020 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"



class TestPluginUpdate:
    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop)
        # fill the routes table
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    RUN_TESTS_BEFORE_210_VERSION = False if common.get_version() <= "2.1.0" else True

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    @pytest.mark.parametrize("param", ["blah", 1, "notificationDelivery", "notificationRule"])
    async def test_bad_type_plugin(self, client, param):
        resp = await client.put('/fledge/plugins/{}/name/update'.format(param), data=None)
        assert 400 == resp.status
        assert "Invalid plugin type. Must be one of 'south' , north', 'filter', 'notify' or 'rule'" == resp.reason

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    @pytest.mark.parametrize("name", ["OMF", "omf", "Omf"])
    async def test_bad_update_of_inbuilt_plugin(self, client, name):
        resp = await client.put('/fledge/plugins/north/{}/update'.format(name), data=None)
        assert 400 == resp.status
        assert "Cannot update an inbuilt OMF plugin." == resp.reason

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    @pytest.mark.parametrize("_type, plugin_installed_dirname", [
        ('south', 'Random'),
        ('north', 'http_north')
    ])
    async def test_package_already_in_progress(self, client, _type, plugin_installed_dirname):
        async def async_mock(return_value):
            return return_value

        pkg_name = "fledge-{}-{}".format(_type, plugin_installed_dirname.lower().replace("_", "-"))
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "update",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}

        select_row_resp = {'count': 1, 'rows': [{
            "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
            "name": pkg_name,
            "action": "update",
            "status": -1,
            "log_file_uri": ""
        }]}
        msg = '{} package update already in progress.'.format(pkg_name)
        storage_client_mock = MagicMock(StorageClientAsync)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(select_row_resp)
        else:
            _rv = asyncio.ensure_future(async_mock(select_row_resp))

        plugin_installed = [{"name": plugin_installed_dirname, "type": _type, "description": "{} plugin".format(_type),
                             "version": "2.1.0", "installedDirectory": "{}/{}".format(_type, plugin_installed_dirname),
                             "packageName": pkg_name}]
        with patch.object(PluginDiscovery, 'get_plugins_installed',
                          return_value=plugin_installed) as plugin_installed_patch:
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'query_tbl_with_payload',
                                  return_value=_rv) as query_tbl_patch:
                    resp = await client.put('/fledge/plugins/{}/{}/update'.format(_type, plugin_installed_dirname),
                                            data=None)
                    assert 429 == resp.status
                    assert msg == resp.reason
                    r = await resp.text()
                    actual = json.loads(r)
                    assert {'message': msg} == actual
                args, kwargs = query_tbl_patch.call_args_list[0]
                assert 'packages' == args[0]
                assert payload == json.loads(args[1])
        plugin_installed_patch.assert_called_once_with(_type, False)

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    @pytest.mark.parametrize("_type, plugin_installed_dirname", [
        ('south', 'Random'),
        ('north', 'http_north')
    ])
    async def test_plugin_not_found(self, client, _type, plugin_installed_dirname):
        plugin_name = 'sinusoid'
        pkg_name = "fledge-{}-{}".format(_type, plugin_installed_dirname.lower().replace("_", "-"))
        plugin_installed = [{"name": plugin_name, "type": _type, "description": "{} plugin".format(_type),
                             "version": "1.8.1", "installedDirectory": "{}/{}".format(_type, plugin_name),
                             "packageName": pkg_name}]
        with patch.object(PluginDiscovery, 'get_plugins_installed',
                          return_value=plugin_installed) as plugin_installed_patch:
            resp = await client.put('/fledge/plugins/{}/{}/update'.format(_type, plugin_installed_dirname), data=None)
            assert 404 == resp.status
            assert "'{} plugin is not yet installed. So update is not possible.'".format(
                plugin_installed_dirname) == resp.reason
        plugin_installed_patch.assert_called_once_with(_type, False)

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    @pytest.mark.parametrize("_type, plugin_installed_dirname", [
        ('south', 'Random'),
        ('north', 'http_north')
    ])
    async def test_plugin_update_when_not_in_use(self, client, _type, plugin_installed_dirname):
        async def async_mock(return_value):
            return return_value

        pkg_name = "fledge-{}-{}".format(_type, plugin_installed_dirname.lower().replace("_", "-"))
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "update",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        plugin_installed = [{"name": plugin_installed_dirname, "type": _type,
                             "description": "{} plugin".format(_type), "version": "1.8.1",
                             "installedDirectory": "{}/{}".format(_type, plugin_installed_dirname),
                             "packageName": pkg_name}]
        insert = {"response": "inserted", "rows_affected": 1}
        insert_row = {'count': 1, 'rows': [{
                "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
                "name": plugin_installed_dirname,
                "action": "update",
                "status": -1,
                "log_file_uri": ""
            }]}
        svc_name = 'R1'
        tracked_plugins = [{'plugin': 'sinusoid', 'service': 'S1'}, {'plugin': 'Random', 'service': svc_name},
                           {'plugin': 'http_north', 'service': svc_name}]
        sch_info = [{'id': '6637c9ff-7090-4774-abca-07dee59a0610', 'enabled': 'f'}]
        storage_client_mock = MagicMock(StorageClientAsync)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock(tracked_plugins)
            _rv2 = await async_mock(sch_info)
            _rv3 = await async_mock(insert)
            _se1 = await async_mock({'count': 0, 'rows': []})
            _se2 = await async_mock(insert_row)
        else:
            _rv1 = asyncio.ensure_future(async_mock(tracked_plugins))
            _rv2 = asyncio.ensure_future(async_mock(sch_info))
            _rv3 = asyncio.ensure_future(async_mock(insert))
            _se1 = asyncio.ensure_future(async_mock({'count': 0, 'rows': []}))
            _se2 = asyncio.ensure_future(async_mock(insert_row))           
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              side_effect=[_se1, _se2]) as query_tbl_patch:
                with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=plugin_installed
                                  ) as plugin_installed_patch:
                    with patch.object(plugins_update, '_get_plugin_and_sch_name_from_asset_tracker',
                                      return_value=_rv1) as plugin_tracked_patch:
                        with patch.object(plugins_update, '_get_sch_id_and_enabled_by_name',
                                          return_value=_rv2) as schedule_patch:
                            with patch.object(storage_client_mock, 'insert_into_tbl',
                                              return_value=_rv3) as insert_tbl_patch:
                                with patch('multiprocessing.Process'):
                                    resp = await client.put('/fledge/plugins/{}/{}/update'.format(
                                        _type, plugin_installed_dirname), data=None)
                                    assert 200 == resp.status
                                    result = await resp.text()
                                    response = json.loads(result)
                                    assert 'id' in response
                                    assert '{} update started.'.format(pkg_name) == response['message']
                                    assert response['statusLink'].startswith('fledge/package/update/status?id=')
                            args, kwargs = insert_tbl_patch.call_args_list[0]
                            assert 'packages' == args[0]
                            actual = json.loads(args[1])
                            assert 'id' in actual
                            assert pkg_name == actual['name']
                            assert 'update' == actual['action']
                            assert -1 == actual['status']
                            assert '' == actual['log_file_uri']
                        schedule_patch.assert_called_once_with(svc_name)
                    plugin_tracked_patch.assert_called_once_with(_type)
                plugin_installed_patch.assert_called_once_with(_type, False)
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    @pytest.mark.parametrize("_type, plugin_installed_dirname", [
        ('south', 'Random'),
        ('north', 'http_north')
    ])
    async def test_plugin_update_when_in_use(self, client, _type, plugin_installed_dirname):
        async def async_mock(return_value):
            return return_value

        pkg_name = "fledge-{}-{}".format(_type, plugin_installed_dirname.lower().replace("_", "-"))
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "update",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        select_row_resp = {'count': 1, 'rows': [{
            "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
            "name": pkg_name,
            "action": "purge",
            "status": 0,
            "log_file_uri": ""
        }]}
        delete = {"response": "deleted", "rows_affected": 1}
        delete_payload = {"where": {"column": "action", "condition": "=", "value": "update",
                                    "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        plugin_installed = [{"name": plugin_installed_dirname, "type": _type,
                             "description": "{} plugin".format(_type), "version": "1.8.1",
                             "installedDirectory": "{}/{}".format(_type, plugin_installed_dirname),
                             "packageName": pkg_name}]
        insert = {"response": "inserted", "rows_affected": 1}
        insert_row = {'count': 1, 'rows': [
            {"id": "c5648940-31ec-4f78-a7a5-b1707e8fe578", "name": plugin_installed_dirname, "action": "update",
             "status": -1, "log_file_uri": ""}]}
        svc_name = 'R1'
        tracked_plugins = [{'plugin': 'sinusoid', 'service': 'S1'}, {'plugin': 'Random', 'service': svc_name},
                           {'plugin': 'http_north', 'service': svc_name}]
        sch_info = [{'id': '6637c9ff-7090-4774-abca-07dee59a0610', 'enabled': 't'}]
        server.Server.scheduler = Scheduler(None, None)
        storage_client_mock = MagicMock(StorageClientAsync)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock(tracked_plugins)
            _rv2 = await async_mock(sch_info)
            _rv3 = await async_mock(insert)
            _rv4 = await async_mock(delete)
            _rv5 = await async_mock((True, "Schedule successfully disabled"))
            _se1 = await async_mock(select_row_resp)
            _se2 = await async_mock(insert_row)
        else:
            _rv1 = asyncio.ensure_future(async_mock(tracked_plugins))
            _rv2 = asyncio.ensure_future(async_mock(sch_info))
            _rv3 = asyncio.ensure_future(async_mock(insert))
            _rv4 = asyncio.ensure_future(async_mock(delete))
            _rv5 = asyncio.ensure_future(async_mock((True, "Schedule successfully disabled")))
            _se1 = asyncio.ensure_future(async_mock(select_row_resp))
            _se2 = asyncio.ensure_future(async_mock(insert_row))    

        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              side_effect=[_se1, _se2]) as query_tbl_patch:
                with patch.object(storage_client_mock, 'delete_from_tbl',
                                  return_value=_rv4) as delete_tbl_patch:
                    with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=plugin_installed
                                      ) as plugin_installed_patch:
                        with patch.object(plugins_update, '_get_plugin_and_sch_name_from_asset_tracker',
                                          return_value=_rv1) as plugin_tracked_patch:
                            with patch.object(plugins_update, '_get_sch_id_and_enabled_by_name',
                                              return_value=_rv2) as schedule_patch:
                                with patch.object(server.Server.scheduler, 'disable_schedule', return_value=_rv5) as disable_sch_patch:
                                    with patch.object(plugins_update._logger, "warning") as log_warn_patch:
                                        with patch.object(storage_client_mock, 'insert_into_tbl',
                                                          return_value=_rv3) as insert_tbl_patch:
                                            with patch('multiprocessing.Process'):
                                                resp = await client.put('/fledge/plugins/{}/{}/update'.format(
                                                    _type, plugin_installed_dirname), data=None)
                                                server.Server.scheduler = None
                                                assert 200 == resp.status
                                                result = await resp.text()
                                                response = json.loads(result)
                                                assert 'id' in response
                                                assert '{} update started.'.format(pkg_name) == response['message']
                                                assert response['statusLink'].startswith(
                                                    'fledge/package/update/status?id=')
                                        args, kwargs = insert_tbl_patch.call_args_list[0]
                                        assert 'packages' == args[0]
                                        actual = json.loads(args[1])
                                        assert 'id' in actual
                                        assert pkg_name == actual['name']
                                        assert 'update' == actual['action']
                                        assert -1 == actual['status']
                                        assert '' == actual['log_file_uri']
                                    assert 1 == log_warn_patch.call_count
                                    log_warn_patch.assert_called_once_with(
                                        'Disabling {} {} instance, as {} plugin is being updated...'.format(
                                            svc_name, _type, plugin_installed_dirname))
                                disable_sch_patch.assert_called_once_with(uuid.UUID(sch_info[0]['id']))
                            schedule_patch.assert_called_once_with(svc_name)
                        plugin_tracked_patch.assert_called_once_with(_type)
                    plugin_installed_patch.assert_called_once_with(_type, False)
                args, kwargs = delete_tbl_patch.call_args_list[0]
                assert 'packages' == args[0]
                assert delete_payload == json.loads(args[1])
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    async def test_filter_plugin_update_when_not_in_use(self, client, _type='filter', plugin_installed_dirname='delta'):
        async def async_mock(return_value):
            return return_value

        pkg_name = "fledge-{}-{}".format(_type, plugin_installed_dirname.lower())
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "update",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        plugin_installed = [{"name": plugin_installed_dirname, "type": _type,
                             "description": "{} plugin".format(_type), "version": "1.8.1",
                             "installedDirectory": "{}/{}".format(_type, plugin_installed_dirname),
                             "packageName": pkg_name}]
        filter_row = {'count': 1, 'rows': [{'name': plugin_installed_dirname}]}
        insert = {"response": "inserted", "rows_affected": 1}
        insert_row = {'count': 1, 'rows': [{
                "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
                "name": plugin_installed_dirname,
                "action": "update",
                "status": -1,
                "log_file_uri": ""
            }]}
        svc_name = 'R1'
        tracked_plugins = [{'plugin': 'sinusoid', 'service': 'S1'}, {'plugin': 'Random', 'service': svc_name},
                           {'plugin': 'http_north', 'service': svc_name}, {'plugin': plugin_installed_dirname,
                                                                           'service': svc_name}]
        sch_info = [{'id': '6637c9ff-7090-4774-abca-07dee59a0610', 'enabled': 'f'}]
        storage_client_mock = MagicMock(StorageClientAsync)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock(tracked_plugins)
            _rv2 = await async_mock(sch_info)
            _rv3 = await async_mock(insert)
            _se1 = await async_mock({'count': 0, 'rows': []})
            _se2 = await async_mock(insert_row)
            _se3 = await async_mock(filter_row)
        else:
            _rv1 = asyncio.ensure_future(async_mock(tracked_plugins))
            _rv2 = asyncio.ensure_future(async_mock(sch_info))
            _rv3 = asyncio.ensure_future(async_mock(insert))
            _se1 = asyncio.ensure_future(async_mock({'count': 0, 'rows': []}))
            _se2 = asyncio.ensure_future(async_mock(insert_row))
            _se3 = asyncio.ensure_future(async_mock(filter_row))
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              side_effect=[_se1, _se3, _se2]) as query_tbl_patch:
                with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=plugin_installed
                                  ) as plugin_installed_patch:
                    with patch.object(plugins_update, '_get_plugin_and_sch_name_from_asset_tracker',
                                      return_value=_rv1) as plugin_tracked_patch:
                        with patch.object(plugins_update, '_get_sch_id_and_enabled_by_name',
                                          return_value=_rv2) as schedule_patch:
                            with patch.object(storage_client_mock, 'insert_into_tbl',
                                              return_value=_rv3) as insert_tbl_patch:
                                with patch('multiprocessing.Process'):
                                    resp = await client.put('/fledge/plugins/{}/{}/update'.format(
                                        _type, plugin_installed_dirname), data=None)
                                    assert 200 == resp.status
                                    result = await resp.text()
                                    response = json.loads(result)
                                    assert 'id' in response
                                    assert '{} update started.'.format(pkg_name) == response['message']
                                    assert response['statusLink'].startswith('fledge/package/update/status?id=')
                            args, kwargs = insert_tbl_patch.call_args_list[0]
                            assert 'packages' == args[0]
                            actual = json.loads(args[1])
                            assert 'id' in actual
                            assert pkg_name == actual['name']
                            assert 'update' == actual['action']
                            assert -1 == actual['status']
                            assert '' == actual['log_file_uri']
                        schedule_patch.assert_called_once_with(svc_name)
                    plugin_tracked_patch.assert_called_once_with(_type)
                plugin_installed_patch.assert_called_once_with(_type, False)
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    async def test_filter_update_when_in_use(self, client, _type='filter', plugin_installed_dirname='delta'):
        async def async_mock(return_value):
            return return_value

        pkg_name = "fledge-{}-{}".format(_type, plugin_installed_dirname.lower())
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "update",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        select_row_resp = {'count': 1, 'rows': [{
            "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
            "name": pkg_name,
            "action": "purge",
            "status": 0,
            "log_file_uri": ""
        }]}
        filter_row = {'count': 1, 'rows': [{'name': plugin_installed_dirname}]}
        delete = {"response": "deleted", "rows_affected": 1}
        delete_payload = {"where": {"column": "action", "condition": "=", "value": "update",
                                    "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        plugin_installed = [{"name": plugin_installed_dirname, "type": _type,
                             "description": "{} plugin".format(_type), "version": "1.8.1",
                             "installedDirectory": "{}/{}".format(_type, plugin_installed_dirname),
                             "packageName": pkg_name}]
        insert = {"response": "inserted", "rows_affected": 1}
        insert_row = {'count': 1, 'rows': [
            {"id": "c5648940-31ec-4f78-a7a5-b1707e8fe578", "name": plugin_installed_dirname, "action": "update",
             "status": -1, "log_file_uri": ""}]}
        svc_name = 'R1'
        tracked_plugins = [{'plugin': 'sinusoid', 'service': 'S1'}, {'plugin': 'Random', 'service': svc_name},
                           {'plugin': 'http_north', 'service': svc_name}, {'plugin': plugin_installed_dirname,
                                                                           'service': svc_name}]
        sch_info = [{'id': '6637c9ff-7090-4774-abca-07dee59a0610', 'enabled': 't'}]
        server.Server.scheduler = Scheduler(None, None)
        storage_client_mock = MagicMock(StorageClientAsync)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock(tracked_plugins)
            _rv2 = await async_mock(sch_info)
            _rv3 = await async_mock(insert)
            _rv4 = await async_mock(delete)
            _rv5 = await async_mock((True, "Schedule successfully disabled"))
            _se1 = await async_mock(select_row_resp)
            _se2 = await async_mock(insert_row)
            _se3 = await async_mock(filter_row)
        else:
            _rv1 = asyncio.ensure_future(async_mock(tracked_plugins))
            _rv2 = asyncio.ensure_future(async_mock(sch_info))
            _rv3 = asyncio.ensure_future(async_mock(insert))
            _rv4 = asyncio.ensure_future(async_mock(delete))
            _rv5 = asyncio.ensure_future(async_mock((True, "Schedule successfully disabled")))
            _se1 = asyncio.ensure_future(async_mock(select_row_resp))
            _se2 = asyncio.ensure_future(async_mock(insert_row))
            _se3 = asyncio.ensure_future(async_mock(filter_row))
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              side_effect=[_se1, _se3, _se2]) as query_tbl_patch:
                with patch.object(storage_client_mock, 'delete_from_tbl',
                                  return_value=_rv4) as delete_tbl_patch:
                    with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=plugin_installed
                                      ) as plugin_installed_patch:
                        with patch.object(plugins_update, '_get_plugin_and_sch_name_from_asset_tracker',
                                          return_value=_rv1) as plugin_tracked_patch:
                            with patch.object(plugins_update, '_get_sch_id_and_enabled_by_name',
                                              return_value=_rv2) as schedule_patch:
                                with patch.object(server.Server.scheduler, 'disable_schedule', return_value=_rv5) as disable_sch_patch:
                                    with patch.object(plugins_update._logger, "warning") as log_warn_patch:
                                        with patch.object(storage_client_mock, 'insert_into_tbl',
                                                          return_value=_rv3) as insert_tbl_patch:
                                            with patch('multiprocessing.Process'):
                                                resp = await client.put('/fledge/plugins/{}/{}/update'.format(
                                                    _type, plugin_installed_dirname), data=None)
                                                server.Server.scheduler = None
                                                assert 200 == resp.status
                                                result = await resp.text()
                                                response = json.loads(result)
                                                assert 'id' in response
                                                assert '{} update started.'.format(pkg_name) == response['message']
                                                assert response['statusLink'].startswith(
                                                    'fledge/package/update/status?id=')
                                        args, kwargs = insert_tbl_patch.call_args_list[0]
                                        assert 'packages' == args[0]
                                        actual = json.loads(args[1])
                                        assert 'id' in actual
                                        assert pkg_name == actual['name']
                                        assert 'update' == actual['action']
                                        assert -1 == actual['status']
                                        assert '' == actual['log_file_uri']
                                    assert 1 == log_warn_patch.call_count
                                    log_warn_patch.assert_called_once_with(
                                        'Disabling {} {} instance, as {} plugin is being updated...'.format(
                                            svc_name, _type, plugin_installed_dirname))
                                disable_sch_patch.assert_called_once_with(uuid.UUID(sch_info[0]['id']))
                            schedule_patch.assert_called_once_with(svc_name)
                        plugin_tracked_patch.assert_called_once_with(_type)
                    plugin_installed_patch.assert_called_once_with(_type, False)
                args, kwargs = delete_tbl_patch.call_args_list[0]
                assert 'packages' == args[0]
                assert delete_payload == json.loads(args[1])
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    @pytest.mark.parametrize("_type, plugin_installed_dirname", [
        ('notify', 'Telegram'),
        ('rule', 'OutOfBound')
    ])
    async def test_notify_plugin_update_when_not_in_use(self, client, _type, plugin_installed_dirname):
        async def async_mock(return_value):
            return return_value

        _type = "notify"
        plugin_type_installed_dir = "notificationRule" if _type == 'rule' else "notificationDelivery"
        pkg_name = "fledge-{}-{}".format(_type, plugin_installed_dirname.lower())
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "update",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        plugin_installed = [{"name": plugin_installed_dirname, "type": _type,
                             "description": "{} C plugin".format(plugin_type_installed_dir), "version": "1.8.1",
                             "installedDirectory": "{}/{}".format(plugin_type_installed_dir, plugin_installed_dirname),
                             "packageName": pkg_name}]
        insert = {"response": "inserted", "rows_affected": 1}
        insert_row = {'count': 1, 'rows': [{
                "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
                "name": plugin_installed_dirname,
                "action": "update",
                "status": -1,
                "log_file_uri": ""
            }]}
        sch_info = {'count': 1, 'rows': [{'id': '6637c9ff-7090-4774-abca-07dee59a0610', 'enabled': 'f'}]}
        storage_client_mock = MagicMock(StorageClientAsync)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock(insert)
            _se1 = await async_mock({'count': 0, 'rows': []})
            _se2 = await async_mock(insert_row)
            _se3 = await async_mock(sch_info)
        else:
            _rv1 = asyncio.ensure_future(async_mock(insert))
            _se1 = asyncio.ensure_future(async_mock({'count': 0, 'rows': []}))
            _se2 = asyncio.ensure_future(async_mock(insert_row))
            _se3 = asyncio.ensure_future(async_mock(sch_info))
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              side_effect=[_se1, _se3, _se2]) as query_tbl_patch:
                with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=plugin_installed
                                  ) as plugin_installed_patch:
                    with patch.object(storage_client_mock, 'insert_into_tbl',
                                      return_value=_rv1) as insert_tbl_patch:
                        with patch('multiprocessing.Process'):
                            resp = await client.put('/fledge/plugins/{}/{}/update'.format(
                                _type, plugin_installed_dirname), data=None)
                            assert 200 == resp.status
                            result = await resp.text()
                            response = json.loads(result)
                            assert 'id' in response
                            assert '{} update started.'.format(pkg_name) == response['message']
                            assert response['statusLink'].startswith('fledge/package/update/status?id=')
                    args, kwargs = insert_tbl_patch.call_args_list[0]
                    assert 'packages' == args[0]
                    actual = json.loads(args[1])
                    assert 'id' in actual
                    assert pkg_name == actual['name']
                    assert 'update' == actual['action']
                    assert -1 == actual['status']
                    assert '' == actual['log_file_uri']
                plugin_installed_patch.assert_called_once_with(_type, False)
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])

    @pytest.mark.skipif(RUN_TESTS_BEFORE_210_VERSION, reason="requires lesser or equal to core 2.1.0 version")
    @pytest.mark.parametrize("_type, plugin_installed_dirname", [
        ('notify', 'alexa'),
        ('rule', 'OutOfBound')
    ])
    async def test_notify_plugin_update_when_in_use(self, client, _type, plugin_installed_dirname):
        async def async_mock(return_value):
            return return_value

        plugin_type_installed_dir = "notificationRule" if _type == 'rule' else "notificationDelivery"
        pkg_name = "fledge-{}-{}".format(_type, plugin_installed_dirname.lower())
        payload = {"return": ["status"], "where": {"column": "action", "condition": "=", "value": "update",
                                                   "and": {"column": "name", "condition": "=", "value": pkg_name}}}
        plugin_installed = [{"name": plugin_installed_dirname, "type": _type,
                             "description": "Generate a notification if the values exceeds a configured value",
                             "version": "1.8.1", "installedDirectory": "{}/{}".format(plugin_type_installed_dir,
                                                                                      plugin_installed_dirname),
                             "packageName": pkg_name}]
        insert = {"response": "inserted", "rows_affected": 1}
        insert_row = {'count': 1, 'rows': [{
                "id": "c5648940-31ec-4f78-a7a5-b1707e8fe578",
                "name": plugin_installed_dirname,
                "action": "update",
                "status": -1,
                "log_file_uri": ""
            }]}
        notification_name = "Test Notification"
        parent_name = "Notifications"
        sch_info = {'count': 1, 'rows': [{'id': '6637c9ff-7090-4774-abca-07dee59a0610', 'enabled': 't'}]}
        read_all_child_category_names = [{"parent": parent_name, "child": notification_name}]
        read_cat_val = {"name": {"description": "The name of this notification", "type": "string",
                                 "default": notification_name, "value": notification_name},
                        "description": {"description": "Description of this notification", "type": "string",
                                        "default": "description", "value": "description"},
                        "rule": {"description": "Rule to evaluate", "type": "string",
                                 "default": plugin_installed_dirname, "value": plugin_installed_dirname},
                        "channel": {"description": "Channel to send alert on", "type": "string",
                                    "default": "email", "value": "email"},
                        "notification_type": {"description": "Type of notification", "type": "enumeration",
                                              "options": ["one shot", "retriggered", "toggled"], "default": "one shot",
                                              "value": "one shot"}, "enable": {"description": "Enabled",
                                                                               "type": "boolean", "default": "true",
                                                                               "value": "true"}}
        disable_notification = {"description": "Enabled", "type": "boolean", "default": "true", "value": "false"}
        storage_client_mock = MagicMock(StorageClientAsync)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock(read_all_child_category_names)
            _rv2 = await async_mock(read_cat_val)
            _rv3 = await async_mock(disable_notification)
            _rv4 = await async_mock(insert)
            _se1 = await async_mock({'count': 0, 'rows': []})
            _se2 = await async_mock(insert_row)
            _se3 = await async_mock(sch_info)
        else:
            _rv1 = asyncio.ensure_future(async_mock(read_all_child_category_names))
            _rv2 = asyncio.ensure_future(async_mock(read_cat_val))
            _rv3 = asyncio.ensure_future(async_mock(disable_notification))
            _rv4 = asyncio.ensure_future(async_mock(insert))
            _se1 = asyncio.ensure_future(async_mock({'count': 0, 'rows': []}))
            _se2 = asyncio.ensure_future(async_mock(insert_row))
            _se3 = asyncio.ensure_future(async_mock(sch_info))        
        
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload',
                              side_effect=[_se1, _se3, _se2]) as query_tbl_patch:
                with patch.object(PluginDiscovery, 'get_plugins_installed', return_value=plugin_installed
                                  ) as plugin_installed_patch:
                    with patch.object(ConfigurationManager, '_read_all_child_category_names',
                                      return_value=_rv1) as child_cat_patch:
                        with patch.object(ConfigurationManager, '_read_category_val',
                                          return_value=_rv2) as cat_value_patch:
                            with patch.object(plugins_update._logger, "warning") as log_warn_patch:
                                with patch.object(ConfigurationManager, 'set_category_item_value_entry',
                                                  return_value=_rv3) as set_cat_value_patch:
                                    with patch.object(storage_client_mock, 'insert_into_tbl',
                                                      return_value=_rv4) as insert_tbl_patch:
                                        with patch('multiprocessing.Process'):
                                            resp = await client.put('/fledge/plugins/{}/{}/update'.format(
                                                _type, plugin_installed_dirname), data=None)
                                            assert 200 == resp.status
                                            result = await resp.text()
                                            response = json.loads(result)
                                            assert 'id' in response
                                            assert '{} update started.'.format(pkg_name) == response['message']
                                            assert response['statusLink'].startswith('fledge/package/update/status?id=')
                                    args, kwargs = insert_tbl_patch.call_args_list[0]
                                    assert 'packages' == args[0]
                                    actual = json.loads(args[1])
                                    assert 'id' in actual
                                    assert pkg_name == actual['name']
                                    assert 'update' == actual['action']
                                    assert -1 == actual['status']
                                    assert '' == actual['log_file_uri']
                                set_cat_value_patch.assert_called_once_with(notification_name, 'enable', 'false')
                            assert 1 == log_warn_patch.call_count
                            log_warn_patch.assert_called_once_with(
                                'Disabling {} notification instance, as {} {} plugin is being updated...'.format(
                                    notification_name, plugin_installed_dirname, _type))
                        cat_value_patch.assert_called_once_with(notification_name)
                    child_cat_patch.assert_called_once_with(parent_name)
                plugin_installed_patch.assert_called_once_with(_type, False)
            args, kwargs = query_tbl_patch.call_args_list[0]
            assert 'packages' == args[0]
            assert payload == json.loads(args[1])
