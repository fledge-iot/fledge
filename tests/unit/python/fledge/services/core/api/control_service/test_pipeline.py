import asyncio
import json
import sys

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from aiohttp import web

from fledge.common.audit_logger import AuditLogger
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.web import middleware
from fledge.services.core import connect
from fledge.services.core import routes
from fledge.services.core import server
from fledge.services.core.api.control_service import pipeline
from fledge.services.core.scheduler.entities import StartUpSchedule
from fledge.services.core.scheduler.scheduler import Scheduler


__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2024 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


async def mock_coro(*args, **kwargs):
    return None if len(args) == 0 else args[0]

SOURCE_LOOKUP = [{'cpsid': 1, 'name': 'Any', 'description': 'Any source.'},
         {'cpsid': 2, 'name': 'Service', 'description': 'A named service in source of the control pipeline.'},
         {'cpsid': 3, 'name': 'API', 'description': 'The control pipeline source is the REST API.'},
         {'cpsid': 4, 'name': 'Notification', 'description': 'The control pipeline originated from a notification.'},
         {'cpsid': 5, 'name': 'Schedule', 'description': 'The control request was triggered by a schedule.'},
         {'cpsid': 6, 'name': 'Script', 'description': 'The control request has come from the named script.'}]

DESTINATION_LOOKUP = [{'cpdid': 1, 'name': 'Any', 'description': 'Any destination.'},
            {'cpdid': 2, 'name': 'Service', 'description': 'A name of service that is being controlled.'},
            {'cpdid': 3, 'name': 'Asset', 'description': 'A name of asset that is being controlled.'},
            {'cpdid': 4, 'name': 'Script', 'description': 'A name of script that will be executed.'},
            {'cpdid': 5, 'name': 'Broadcast', 'description': 'No name is applied and pipeline will be considered for any'
                                                             ' control writes or operations to broadcast destinations.'}]

class TestPipeline:
    """ Pipeline API tests """

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    @pytest.mark.parametrize("request_param", [
        '', '?type=source', '?type=destination', '?type=blah'
    ])
    async def test_get_lookup(self, client, request_param):
        storage_result = {"controlLookup": {"source": [], "destination": []}}
        rv = await mock_coro(storage_result) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(storage_result))
        with patch.object(pipeline, '_get_all_lookups', return_value=rv) as patch_lookup:
            resp = await client.get('/fledge/control/lookup{}'.format(request_param))
            assert 200 == resp.status
            json_response = json.loads(await resp.text())
            assert 'controlLookup' in json_response
        if request_param.endswith('source'):
            patch_lookup.assert_called_once_with("control_source")
        elif request_param.endswith('destination'):
            patch_lookup.assert_called_once_with("control_destination")
        else:
            patch_lookup.assert_called_once_with()

    async def test_bad_get_lookup(self, client):
        with patch.object(pipeline, '_get_all_lookups', side_effect=Exception) as patch_lookup:
            with patch.object(pipeline._logger, 'error') as patch_logger:
                resp = await client.get('/fledge/control/lookup')
                assert 500 == resp.status
                assert '' == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": ""} == json_response
            patch_logger.assert_called()
        patch_lookup.assert_called_once_with()

    async def test_get_all_when_empty(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        storage_result = {'count': 0, 'rows': []}
        expected_api_response = {"pipelines": []}
        if sys.version_info >= (3, 8):
            rv = await mock_coro(storage_result)
            source_lookup = await mock_coro([])
            dest_lookup = await mock_coro([])
        else:
            rv = asyncio.ensure_future(mock_coro(storage_result))
            source_lookup = asyncio.ensure_future(mock_coro([]))
            dest_lookup = asyncio.ensure_future(mock_coro([]))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=rv) as patch_query_tbl:
                with patch.object(pipeline, '_get_all_lookups', side_effect=[source_lookup, dest_lookup]):
                    resp = await client.get('/fledge/control/pipeline')
                    assert 200 == resp.status
                    json_response = json.loads(await resp.text())
                    assert 'pipelines' in json_response
                    assert expected_api_response == json_response
            patch_query_tbl.assert_called_once_with('control_pipelines')

    async def test_get_all(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        storage_result = {'count': 2, 'rows': [
            {'cpid': 1, 'name': 'Cp1', 'stype': 1, 'sname': '', 'dtype': 5, 'dname': '', 'enabled': 't',
             'execution': 'Shared'}, {'cpid': 2, 'name': 'cp2', 'stype': 3, 'sname': 'anonymous', 'dtype': 1,
                                      'dname': '', 'enabled': 't', 'execution': 'Exclusive'}]}
        expected_api_response = {'pipelines': [{'id': 1, 'name': 'Cp1', 'source': {'type': 'Any', 'name': ''},
                        'destination': {'type': 'Broadcast', 'name': ''}, 'enabled': True, 'execution': 'Shared',
                        'filters': []}, {'id': 2, 'name': 'cp2', 'source': {'type': 'API', 'name': 'anonymous'},
                                         'destination': {'type': 'Any', 'name': ''}, 'enabled': True,
                                         'execution': 'Exclusive', 'filters': []}]}

        filters_storage_result = {'count': 0, 'rows': []}
        if sys.version_info >= (3, 8):
            rv = await mock_coro(storage_result)
            source_lookup = await mock_coro(SOURCE_LOOKUP)
            dest_lookup = await mock_coro(DESTINATION_LOOKUP)
            filters = await mock_coro(filters_storage_result)
        else:
            rv = asyncio.ensure_future(mock_coro(storage_result))
            source_lookup = asyncio.ensure_future(mock_coro(SOURCE_LOOKUP))
            dest_lookup = asyncio.ensure_future(mock_coro(DESTINATION_LOOKUP))
            filters = asyncio.ensure_future(mock_coro(filters_storage_result))

        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=rv) as patch_query_tbl:
                with patch.object(pipeline, '_get_all_lookups', side_effect=[source_lookup, dest_lookup]):
                    with patch.object(pipeline, '_get_table_column_by_value', return_value=filters
                                      ) as patch_filters:
                        resp = await client.get('/fledge/control/pipeline')
                        assert 200 == resp.status
                        json_response = json.loads(await resp.text())
                        assert 'pipelines' in json_response
                        assert expected_api_response == json_response
                    assert 2 == patch_filters.call_count
                    args = patch_filters.call_args_list
                    args1, _ = args[0]
                    assert ('control_filters', 'cpid', 1) == args1
                    args2, _ = args[1]
                    assert ('control_filters', 'cpid', 2) == args2
            patch_query_tbl.assert_called_once_with('control_pipelines')

    async def test_bad_get_all(self, client):
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', side_effect=Exception) as patch_query_tbl:
                with patch.object(pipeline._logger, 'error') as patch_logger:
                    resp = await client.get('/fledge/control/pipeline')
                    assert 500 == resp.status
                    assert "" == resp.reason
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {"message": ""} == json_response
                patch_logger.assert_called()
                args, _ = patch_logger.call_args_list[0]
                assert 'Failed to get all pipelines.' == args[1]
            patch_query_tbl.assert_called_once_with('control_pipelines')

    async def test_get_by_id(self, client):
        cpid = 1
        storage_result = {'id': cpid, 'name': 'Cp1', 'source': {'type': 'Any', 'name': ''}, 'destination':
            {'type': 'Broadcast', 'name': ''}, 'enabled': True, 'execution': 'Shared', 'filters': []}
        rv = await mock_coro(storage_result) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(storage_result))
        with patch.object(pipeline, '_get_pipeline', return_value=rv) as patch_pipeline:
            resp = await client.get('/fledge/control/pipeline/{}'.format(cpid))
            assert 200 == resp.status
            json_response = json.loads(await resp.text())
            assert storage_result == json_response
            assert isinstance(json_response['id'], int)
        patch_pipeline.assert_called_once_with(str(cpid))

    @pytest.mark.parametrize("exception_name, status_code", [
        (ValueError, 400),
        (KeyError, 404),
        (Exception, 500),
    ])
    async def test_bad_get_by_id(self, client, exception_name, status_code):
        cpid = 1
        with patch.object(pipeline, '_get_pipeline', side_effect=exception_name) as patch_pipeline:
            with patch.object(pipeline._logger, 'error') as patch_logger:
                resp = await client.get('/fledge/control/pipeline/{}'.format(cpid))
                assert status_code == resp.status
                assert '' == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": ""} == json_response
            if exception_name == Exception:
                patch_logger.assert_called()
                args, _ = patch_logger.call_args_list[0]
                assert 'Failed to fetch details of pipeline having ID: <{}>.'.format(cpid) == args[1]
        patch_pipeline.assert_called_once_with(str(cpid))

    async def test_create(self, client):
        data = {"name": "wildcard", "enabled": True, "execution": "shared", "source": {"type": 1},
                   "destination": {"type": 1}}
        columns = {'name': 'wildcard', 'enabled': 't', 'execution': 'shared', 'stype': 1, 'sname': '',
                   'dtype': 1, 'dname': ''}
        insert_column = ('{"name": "wildcard", "enabled": "t", "execution": "shared", "stype": 1, "sname": "", '
                         '"dtype": 1, "dname": ""}')
        insert_result = {'response': 'inserted', 'rows_affected': 1}
        in_use = {'name': 'wildcard', 'stype': 1, 'sname': '', 'dtype': 1, 'dname': '', 'enabled': 't',
                  'execution': 'shared', 'id': 4}
        expected_pipeline =  {'name': 'wildcard', 'enabled': True, 'execution': 'shared', 'id': 4,
                              'source': {'type': 'Any', 'name': ''}, 'destination': {'type': 'Any', 'name': ''},
                              'filters': []}
        storage_client_mock = MagicMock(StorageClientAsync)
        if sys.version_info >= (3, 8):
            rv = await mock_coro(columns)
            rv2 = await mock_coro(insert_result)
            rv3 = await mock_coro(in_use)
            rv4 = await mock_coro("Any")
            rv5 = await mock_coro("Any")
            rv6 = await mock_coro(None)
        else:
            rv = asyncio.ensure_future(mock_coro(columns))
            rv2 = asyncio.ensure_future(mock_coro(insert_result))
            rv3 = asyncio.ensure_future(mock_coro(in_use))
            rv4 = asyncio.ensure_future(mock_coro("Any"))
            rv5 = asyncio.ensure_future(mock_coro("Any"))
            rv6 = asyncio.ensure_future(mock_coro(None))
        with patch.object(pipeline, '_check_parameters', return_value=rv) as patch_params:
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value=rv2) as patch_insert_tbl:
                    with patch.object(pipeline, '_pipeline_in_use', return_value=rv3) as patch_in_use:
                        with patch.object(pipeline, '_get_lookup_value', side_effect=[rv4, rv5]):
                            with patch.object(AuditLogger, '__init__', return_value=None):
                                with patch.object(AuditLogger, 'information', return_value=rv6) as patch_audit:
                                    resp = await client.post('/fledge/control/pipeline', data=json.dumps(data))
                                    assert 200 == resp.status
                                    result = await resp.text()
                                    json_response = json.loads(result)
                                    assert expected_pipeline == json_response
                                patch_audit.assert_called_once_with('CTPAD', expected_pipeline)
                    patch_in_use.assert_called_once_with(data['name'],
                                                         {'type': data['source']['type'], 'name': ''},
                                                         {'type': data['destination']['type'], 'name': ''}, info=True)
                patch_insert_tbl.assert_called_once_with('control_pipelines', insert_column)
        args, _ = patch_params.call_args_list[0]
        assert data == args[0]

    @pytest.mark.parametrize("exception_name, status_code", [
        (ValueError, 400),
        (KeyError, 404),
        (Exception, 500),
    ])
    async def test_bad_create(self, client, exception_name, status_code):
        payload = {"name": "Cp"}
        with patch.object(pipeline, '_check_parameters', side_effect=exception_name):
            with patch.object(pipeline._logger, 'error') as patch_logger:
                resp = await client.post('/fledge/control/pipeline', data=json.dumps(payload))
                assert status_code == resp.status
                assert '' == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": ""} == json_response
            if exception_name == Exception:
                patch_logger.assert_called()
                args, _ = patch_logger.call_args_list[0]
                assert 'Failed to create pipeline: {}.'.format(payload['name']) == args[1]

    async def test_update(self, client):
        cpid = 1
        storage_result = {'id': cpid, 'name': 'Cp1', 'source': {'type': 'Any', 'name': ''}, 'destination':
            {'type': 'Broadcast', 'name': ''}, 'enabled': True, 'execution': 'Shared', 'filters': []}
        column_payload =  ('{"values": {"enabled": "t", "execution": "Shared", "stype": 3, "sname": "anonymous", '
                           '"dtype": 1, "dname": ""}, "where": {"column": "cpid", "condition": "=", "value": 1}}')
        payload = {'execution': 'Shared', 'source': {'type': 3, 'name': None}, 'destination': {'type': 1, 'name': None},
                   'filters': [], 'enabled': True}
        columns = {'enabled': 't', 'execution': 'Shared', 'stype': 3, 'sname': 'anonymous', 'dtype': 1, 'dname': ''}
        storage_client_mock = MagicMock(StorageClientAsync)
        rows_affected = {"response": "updated", "rows_affected": 1}
        update_pipeline = {'id': cpid, 'name': 'Cp1', 'source': {'type': 'API', 'name': ''}, 'destination':
            {'type': 'Any', 'name': ''}, 'enabled': True, 'execution': 'Shared', 'filters': []}
        if sys.version_info >= (3, 8):
            rv = await mock_coro(storage_result)
            rv2 = await mock_coro(columns)
            rv3 = await mock_coro(rows_affected)
            rv4 = await mock_coro(None)
            rv5 = await mock_coro(update_pipeline)
        else:
            rv = asyncio.ensure_future(mock_coro(storage_result))
            rv2 = asyncio.ensure_future(mock_coro(columns))
            rv3 = asyncio.ensure_future(mock_coro(rows_affected))
            rv4 = asyncio.ensure_future(mock_coro(None))
            rv5 = asyncio.ensure_future(mock_coro(update_pipeline))
        with patch.object(pipeline, '_get_pipeline', side_effect=[rv, rv5]) as patch_pipeline:
            with patch.object(pipeline, '_check_parameters', return_value=rv2) as patch_params:
                with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                    with patch.object(storage_client_mock, 'update_tbl', return_value=rv3) as patch_update_tbl:
                        with patch.object(AuditLogger, '__init__', return_value=None):
                            with patch.object(AuditLogger, 'information', return_value=rv4) as patch_audit:
                                resp = await client.put('/fledge/control/pipeline/{}'.format(cpid),
                                                        data=json.dumps(payload))
                                assert 200 == resp.status
                                result = await resp.text()
                                json_response = json.loads(result)
                                assert {"message": 'Control Pipeline with ID:<{}> has been updated successfully.'
                                                   ''.format(cpid)} == json_response
                            patch_audit.assert_called_once_with('CTPCH', {"pipeline": update_pipeline,
                                                                               "old_pipeline": storage_result})
                        patch_update_tbl.assert_called_once_with('control_pipelines', column_payload)
            args, _ = patch_params.call_args_list[0]
            payload['old_pipeline_name'] = storage_result['name']
            assert payload == args[0]
        assert 2 == patch_pipeline.call_count

    @pytest.mark.parametrize("exception_name, status_code", [
            (ValueError, 400),
            (KeyError, 404),
            (Exception, 500),
    ])
    async def test_bad_update(self, client, exception_name, status_code):
        cpid = 1
        with patch.object(pipeline, '_get_pipeline', side_effect=exception_name) as patch_pipeline:
            with patch.object(pipeline._logger, 'error') as patch_logger:
                resp = await client.put('/fledge/control/pipeline/{}'.format(cpid))
                assert status_code == resp.status
                assert '' == resp.reason
                result = await resp.text()
                json_response = json.loads(result)
                assert {"message": ""} == json_response
            if exception_name == Exception:
                patch_logger.assert_called()
                args, _ = patch_logger.call_args_list[0]
                assert 'Failed to update pipeline having ID: <{}>.'.format(cpid) == args[1]
        patch_pipeline.assert_called_once_with(str(cpid))

    async def test_delete(self, client):
        cpid = 1
        storage_client_mock = MagicMock(StorageClientAsync)
        del_payload = '{"where": {"column": "cpid", "condition": "=", "value": 1}}'
        storage_result = {'id': cpid, 'name': 'Cp1', 'source': {'type': 'Any', 'name': ''}, 'destination':
            {'type': 'Broadcast', 'name': ''}, 'enabled': True, 'execution': 'Shared', 'filters': []}
        rows_affected = {"response": "deleted", "rows_affected": 1}
        message = {'message': 'Control Pipeline with ID:<{}> has been deleted successfully.'.format(cpid),
                   'name': storage_result['name']}
        if sys.version_info >= (3, 8):
            rv = await mock_coro(storage_result)
            rv2 = await mock_coro(None)
            rv3 = await mock_coro(rows_affected)
        else:
            rv = asyncio.ensure_future(mock_coro(storage_result))
            rv2 = asyncio.ensure_future(mock_coro(None))
            rv3 = asyncio.ensure_future(mock_coro(rows_affected))
        with patch.object(pipeline, '_get_pipeline', return_value=rv) as patch_pipeline:
            with patch.object(pipeline, '_remove_filters', return_value=rv2) as patch_filters:
                with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                    with patch.object(storage_client_mock, 'delete_from_tbl', return_value=rv3
                                      ) as patch_delete_tbl:
                        with patch.object(AuditLogger, '__init__', return_value=None):
                            with patch.object(AuditLogger, 'information', return_value=rv2) as patch_audit:
                                resp = await client.delete('/fledge/control/pipeline/{}'.format(cpid))
                                assert 200 == resp.status
                                json_response = json.loads(await resp.text())
                                assert message == json_response
                            patch_audit.assert_called_once_with('CTPDL', message)
                    patch_delete_tbl.assert_called_once_with('control_pipelines', del_payload)
            patch_filters.assert_called_once_with(storage_client_mock, [], cpid, storage_result['name'])
        patch_pipeline.assert_called_once_with(str(cpid))

    @pytest.mark.parametrize("exception_name, status_code", [
        (ValueError, 400),
        (KeyError, 404),
        (Exception, 500),
    ])
    async def test_bad_delete(self, client, exception_name, status_code):
        cpid = 1
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(pipeline, '_get_pipeline', side_effect=exception_name) as patch_pipeline:
                with patch.object(pipeline._logger, 'error') as patch_logger:
                    resp = await client.delete('/fledge/control/pipeline/{}'.format(cpid))
                    assert status_code == resp.status
                    assert '' == resp.reason
                    result = await resp.text()
                    json_response = json.loads(result)
                    assert {"message": ""} == json_response
                if exception_name == Exception:
                    patch_logger.assert_called()
                    args, _ = patch_logger.call_args_list[0]
                    assert 'Failed to delete pipeline having ID: <{}>.'.format(cpid) == args[1]
            patch_pipeline.assert_called_once_with(str(cpid))

    async def test__get_all_lookups(self):
        storage_client_mock = MagicMock(StorageClientAsync)
        if sys.version_info >= (3, 8):
            source_lookup = await mock_coro({"rows": SOURCE_LOOKUP})
            dest_lookup = await mock_coro({"rows": DESTINATION_LOOKUP})
        else:
            source_lookup = asyncio.ensure_future(mock_coro({"rows": SOURCE_LOOKUP}))
            dest_lookup = asyncio.ensure_future(mock_coro({"rows": DESTINATION_LOOKUP}))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl',
                              side_effect=[source_lookup, dest_lookup]) as patch_query:
                res = await pipeline._get_all_lookups()
                assert 'source' in res
                assert 'destination' in res
            assert 2 == patch_query.call_count
            args = patch_query.call_args_list
            tbl1, _ = args[0]
            assert 'control_source' == tbl1[0]
            tbl2, _ = args[1]
            assert 'control_destination' == tbl2[0]

    @pytest.mark.parametrize("name", [
        "control_source", "control_destination"
    ])
    async def test__get_all_lookups_by_table(self, name):
        storage_client_mock = MagicMock(StorageClientAsync)
        storage_result = {"rows": SOURCE_LOOKUP} if name == "control_source" else {"rows": DESTINATION_LOOKUP}
        lookup = await mock_coro(storage_result) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(storage_result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl', return_value=lookup) as patch_query:
                res = await pipeline._get_all_lookups(name)
                assert isinstance(res, list)
                assert len(res)
            patch_query.assert_called_once_with(name)

    @pytest.mark.parametrize("tbl_name, column_name, column_value, limit", [
        ("control_filters", "cpid", 2, None),
        ("control_pipelines", "name", "CP", None),
        ("control_source", "name", "Any", None),
        ("control_destination", "name", "Broadcast", None),
        ("control_pipelines", "name", "CP", 1),
    ])
    async def test__get_table_column_by_value(self, tbl_name, column_name, column_value, limit):
        storage_client_mock = MagicMock(StorageClientAsync)
        lookup = await mock_coro({"rows": []}) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro({"rows": []}))
        payload = {"where": {"column": column_name, "condition": "=", "value": column_value}}
        if tbl_name == "control_filters":
            payload["sort"] = {"column": "forder", "direction": "asc"}
        if limit is not None:
            payload["limit"] = limit
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=lookup
                              ) as patch_query_tbl:
                res = await pipeline._get_table_column_by_value(tbl_name, column_name, column_value, limit)
                assert 'rows' in res
                assert not len(res['rows'])
            assert patch_query_tbl.called
            args = patch_query_tbl.call_args_list
            arg, _ = args[0]
            assert tbl_name == arg[0]
            assert payload == json.loads(arg[1])

    async def test_bad__get_pipeline(self):
        cpid = 3
        rv = await mock_coro({"rows": []}) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro({"rows": []}))
        with pytest.raises(Exception) as exc_info:
            with patch.object(pipeline, '_get_table_column_by_value', return_value=rv):
                await pipeline._get_pipeline(cpid, False)
        assert exc_info.type is KeyError
        assert 'Pipeline having ID: {} not found.'.format(cpid) == exc_info.value.args[0]

    async def test__get_pipeline(self):
        cpid = 3
        result = {"rows": [{"cpid": cpid, "name": "CP-3", "stype": 1, "sname": "", "dtype": 5, "dname": "",
                            "enabled": "t", "execution": "Shared"}]}
        if sys.version_info >= (3, 8):
            rv = await mock_coro(result)
            rv2 = await mock_coro("Any")
        else:
            rv = asyncio.ensure_future(mock_coro(result))
            rv2 = asyncio.ensure_future(mock_coro("Any"))
        with patch.object(pipeline, '_get_table_column_by_value', return_value=rv) as patch_tbl:
            with patch.object(pipeline, '_get_lookup_value', return_value=rv2) as patch_lookup:
                res = await pipeline._get_pipeline(cpid, False)
                expected_rows = result["rows"][0]
                assert expected_rows['cpid'] == res['id']
                assert expected_rows['name'] == res['name']
                assert isinstance(res['source']['type'], str)
                assert expected_rows['sname'] == res['source']['name']
                assert isinstance(res['destination']['type'], str)
                assert expected_rows['dname'] == res['destination']['name']
                assert res['enabled'] is True
                assert expected_rows['execution'] == res['execution']
            assert 2 == patch_lookup.call_count
            args = patch_lookup.call_args_list
            arg, _ = args[0]
            assert ('source', result["rows"][0]['stype']) == arg
            arg, _ = args[1]
            assert ('destination', result["rows"][0]['dtype']) == arg
        patch_tbl.assert_called_once_with('control_pipelines', 'cpid', cpid)

    @pytest.mark.parametrize("source, dest, matched, info, info_output", [
        ("s", "d", False, False, None),
        ({'type': 1, 'name': ''}, {'type': 5, 'name': ''}, True, False, None),
        ({'type': 1, 'name': ''}, {'type': 5, 'name': ''}, True, True, True),
        ({'type': 2, 'name': ''}, {'type': 5, 'name': ''}, False, False, None),
        ({'type': 2, 'name': ''}, {'type': 5, 'name': ''}, False, True, None),
        ({'type': 5, 'name': ''}, {'type': 5, 'name': ''}, False, False, None),
        ({'type': 5, 'name': ''}, {'type': 1, 'name': ''}, False, False, None)
    ])
    async def test__pipeline_in_use(self, source, dest, matched, info, info_output):
        name = "Modbus"
        result = {"rows": [{"cpid": 2, "name": name, "stype": 1, "sname": "", "dtype": 5, "dname": "",
                            "enabled": "t", "execution": "Shared"}]}
        rv = await mock_coro(result) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(result))
        with patch.object(pipeline, '_get_table_column_by_value', return_value=rv) as patch_tbl:
            res = await pipeline._pipeline_in_use(name, source, dest, info)
            assert res == result['rows'][0] if info_output else res == info_output if info else res is matched
        patch_tbl.assert_called_once_with('control_pipelines', 'name', name)

    @pytest.mark.parametrize("_type, value, name", [
        ("source", 3, "API"), ("source", 2, "Service"), ("source", 1, "Any"),
        ("source", 4, "Notification"), ("source", 5, "Schedule"), ("source", 6, "Script"),
        ("destination", 1, "Any"), ("destination", 2, "Service"), ("destination", 3, "Asset"),
        ("destination", 4, "Script"), ("destination", 5, "Broadcast")
    ])
    async def test__get_lookup_value(self, _type, value, name):
        storage_result = SOURCE_LOOKUP if _type == "source" else DESTINATION_LOOKUP
        lookup = await mock_coro(storage_result) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(storage_result))
        with patch.object(pipeline, '_get_all_lookups', return_value=lookup) as patch_lookup:
            res = await pipeline._get_lookup_value(_type, value)
            assert name == res
        patch_lookup.assert_called_once_with('control_{}'.format(_type))

    @pytest.mark.parametrize("payload, exception_name, error_msg", [
        ({"name": 1}, ValueError, "Pipeline name should be in string."),
        ({"name": ""}, ValueError, "Pipeline name cannot be empty."),
        ({"name": "Cp", "enabled": 1}, ValueError, "Enabled should be a bool."),
        ({"name": "Cp", "enabled": True, "execution": 1}, ValueError, "Execution should be in string."),
        ({"name": "Cp", "enabled": True, "execution": ""}, ValueError, "Execution value cannot be empty."),
        ({"name": "Cp", "enabled": True, "execution": "inclusive"}, ValueError,
         "Execution model value either shared or exclusive."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": 1}, ValueError,
         "Source should be passed with type and name."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": {"type": "1"}}, ValueError,
         "Source type should be an integer value."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": {"type": 5}}, ValueError,
         "Invalid source type found."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": {"type": 5}}, ValueError,
         "Source name is missing."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": {"type": 5, "name": 1}}, ValueError,
         "Source name should be a string value."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": {"type": 5, "name": ""}}, ValueError,
         "Source name cannot be empty."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": {"name": "Abra"}}, ValueError,
         "Source type is missing."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": {"type": 1}, "destination": 1}, ValueError,
         "Destination should be passed with type and name."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": {"type": 1}, "destination": {"type": "1"}},
         ValueError, "Destination type should be an integer value."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "destination": {"type": 1}},
         ValueError, "Invalid destination type found."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": {"type": 1}, "destination":
            {"type": 2, "name": 1}}, ValueError, "Destination name should be a string value."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": {"type": 1}, "destination":
            {"type": 2, "name": ""}}, ValueError, "Destination name cannot be empty."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": {"type": 1}, "destination":
            {"name": "foo"}}, ValueError, "Destination type is missing."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": {"type": 1}, "destination":{"type": 2}},
          ValueError, "Destination name is missing."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": {"type": 6, "name": "Script"},
          "destination": {"type": 4, "name": "Script"}}, ValueError,
         "Pipeline is not allowed with same type of source and destination."),
        ({"name": "Cp", "enabled": True, "execution": "exclusive", "source": {"type": 5, "name": "Sch"},
          "destination": {"type": 4, "name": "Script"}, "filters": "[]"}, ValueError,
         "Pipeline filters should be passed in list."),
    ])
    async def test_bad__check_parameters(self, payload, exception_name, error_msg):
        req_mock = MagicMock(web.Request)
        storage_result = {"count": 0, "rows": []}
        res = "" if error_msg.endswith("type found.") else "Any"
        if sys.version_info >= (3, 8):
            rv = await mock_coro(storage_result)
            rv2 = await mock_coro(res)
        else:
            rv = asyncio.ensure_future(mock_coro(storage_result))
            rv2 = asyncio.ensure_future(mock_coro(res))
        with pytest.raises(Exception) as exc_info:
            with patch.object(pipeline, '_check_unique_pipeline', return_value=rv):
                with patch.object(pipeline, '_get_lookup_value', return_value=rv2):
                    with patch.object(pipeline, '_validate_lookup_name', return_value=rv2):
                        await pipeline._check_parameters(payload, req_mock)
        assert exc_info.type is exception_name
        assert exc_info.value.args[0] == error_msg

    @pytest.mark.parametrize("lookup, _type, value", [
        ("source", 6, "Sc"), ("destination", 4, "foo")
    ])
    async def test__validate_lookup_name_script(self, lookup, _type, value):
        storage_client_mock = MagicMock(StorageClientAsync)
        storage_result = {"rows": [{"name": "S1"}, {"name": "S2"}]}
        rv = await mock_coro(storage_result) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(storage_result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=rv) as patch_query:
                with pytest.raises(Exception) as exc_info:
                    await pipeline._validate_lookup_name(lookup, _type, value)
                assert exc_info.type is ValueError
                assert "'{}' not a valid script name.".format(value) == exc_info.value.args[0]
            patch_query.assert_called_once_with('control_script', '{"return": ["name"]}')

    async def test__validate_lookup_name_asset(self, lookup="destination", _type=3, value="sinusoid"):
        storage_client_mock = MagicMock(StorageClientAsync)
        storage_result = {"rows": [{"asset": "S1", "event": "Ingest"}, {"asset": "S2", "event": "Egress"}]}
        rv = await mock_coro(storage_result) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(storage_result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(storage_client_mock, 'query_tbl_with_payload', return_value=rv) as patch_query:
                with pytest.raises(Exception) as exc_info:
                    await pipeline._validate_lookup_name(lookup, _type, value)
                assert exc_info.type is ValueError
                assert "'{}' not a valid asset name.".format(value) == exc_info.value.args[0]
            patch_query.assert_called_once_with('asset_tracker', '{"modifier": "distinct", "return": ["asset"]}')

    async def test__validate_lookup_name_notifications(self, lookup="source", _type=4, value="N1"):
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        storage_result = [{"child": ["N"]}]
        rv = await mock_coro(storage_result) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(storage_result))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(c_mgr, '_read_all_child_category_names', return_value=rv) as patch_get_all_items:
                with pytest.raises(Exception) as exc_info:
                    await pipeline._validate_lookup_name(lookup, _type, value)
                #assert exc_info.type is ValueError
                assert "'{}' not a valid notification instance name.".format(value) == exc_info.value.args[0]
            patch_get_all_items.assert_called_once_with('Notifications')

    @pytest.mark.parametrize("lookup, _type, value, error_msg", [
        ("source", 2, "sine", "not a valid service."),
        ("destination", 2, "mod", "not a valid service."),
        ("source", 5, "ninja", "not a valid schedule name.")
    ])
    async def test__validate_lookup_name_schedule(self, lookup, _type, value, error_msg):
        async def mock_schedule(name):
            schedules = []
            schedule = StartUpSchedule()
            schedule.schedule_id = "1"
            schedule.exclusive = True
            schedule.enabled = True
            schedule.name = name
            schedule.process_name = "bar"
            schedule.repeat = timedelta(seconds=30)
            schedule.time = None
            schedule.day = None
            schedules.append(schedule)
            return schedules

        server.Server.scheduler = Scheduler(None, None)
        storage_client_mock = MagicMock(StorageClientAsync)
        get_sch = await mock_schedule("sine") if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_schedule("sine"))
        with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
            with patch.object(server.Server.scheduler, 'get_schedules', return_value=get_sch
                              ) as patch_get_schedules:
                with pytest.raises(Exception) as exc_info:
                    await pipeline._validate_lookup_name(lookup, _type, value)
                    server.Server.scheduler = None
                assert exc_info.type is ValueError
                assert "'{}' {}".format(value, error_msg) == exc_info.value.args[0]
            patch_get_schedules.assert_called_once_with()

    async def test__check_unique_pipeline(self):
        name = "Cp"
        rv = await mock_coro({"rows": [1]}) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro({"rows": [1]}))
        with patch.object(pipeline, '_get_table_column_by_value', return_value=rv) as patch_tbl_col:
            with pytest.raises(Exception) as exc_info:
                await pipeline._check_unique_pipeline(name)
            assert exc_info.type is ValueError
            assert "{} pipeline already exists with the same name.".format(name) == exc_info.value.args[0]
        patch_tbl_col.assert_called_once_with('control_pipelines', 'name', name, limit=1)

class TestPipelineFilters:
    """ Pipeline Filters API tests """

    @pytest.fixture
    def client(self, loop, test_client):
        app = web.Application(loop=loop, middlewares=[middleware.optional_auth_middleware])
        routes.setup(app)
        return loop.run_until_complete(test_client(app))

    async def test_create(self, client):
        data = {"name": "wildcard", "enabled": True, "execution": "shared", "source": {"type": 1},
                   "destination": {"type": 1}, "filters": ["Filter1"]}
        columns = {'name': 'wildcard', 'enabled': 't', 'execution': 'shared', 'stype': 1, 'sname': '',
                   'dtype': 1, 'dname': ''}
        insert_column = ('{"name": "wildcard", "enabled": "t", "execution": "shared", "stype": 1, "sname": "", '
                         '"dtype": 1, "dname": ""}')
        insert_result = {'response': 'inserted', 'rows_affected': 1}
        in_use = {'name': 'wildcard', 'stype': 1, 'sname': '', 'dtype': 1, 'dname': '', 'enabled': 't',
                  'execution': 'shared', 'id': 4}
        expected_pipeline =  {'name': 'wildcard', 'enabled': True, 'execution': 'shared', 'id': 4,
                              'source': {'type': 'Any', 'name': ''}, 'destination': {'type': 'Any', 'name': ''},
                              'filters': ["Filter1"]}
        storage_client_mock = MagicMock(StorageClientAsync)
        if sys.version_info >= (3, 8):
            rv = await mock_coro(columns)
            rv2 = await mock_coro(insert_result)
            rv3 = await mock_coro(in_use)
            rv4 = await mock_coro("Any")
            rv5 = await mock_coro("Any")
            rv6 = await mock_coro(None)
            rv7 = await mock_coro(True)
            rv8 = await mock_coro(["Filter1"])
        else:
            rv = asyncio.ensure_future(mock_coro(columns))
            rv2 = asyncio.ensure_future(mock_coro(insert_result))
            rv3 = asyncio.ensure_future(mock_coro(in_use))
            rv4 = asyncio.ensure_future(mock_coro("Any"))
            rv5 = asyncio.ensure_future(mock_coro("Any"))
            rv6 = asyncio.ensure_future(mock_coro(None))
            rv7 = asyncio.ensure_future(mock_coro(True))
            rv8 = asyncio.ensure_future(mock_coro(["Filter1"]))
        with patch.object(pipeline, '_check_parameters', return_value=rv) as patch_params:
            with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value=rv2) as patch_insert_tbl:
                    with patch.object(pipeline, '_pipeline_in_use', return_value=rv3) as patch_in_use:
                        with patch.object(pipeline, '_get_lookup_value', side_effect=[rv4, rv5]):
                            with patch.object(pipeline, '_check_filters', return_value=rv7
                                              ) as patch_check_filter:
                                with patch.object(pipeline, '_update_filters', return_value=rv8
                                                  ) as patch_update_filter:
                                    with patch.object(AuditLogger, '__init__', return_value=None):
                                        with patch.object(AuditLogger, 'information', return_value=rv6
                                                          ) as patch_audit:
                                            resp = await client.post('/fledge/control/pipeline', data=json.dumps(data))
                                            assert 200 == resp.status
                                            result = await resp.text()
                                            json_response = json.loads(result)
                                            assert expected_pipeline == json_response
                                        patch_audit.assert_called_once_with('CTPAD', expected_pipeline)
                                patch_update_filter.assert_called_once_with(storage_client_mock, in_use['id'],
                                                                            data['name'], data['filters'])
                            patch_check_filter.assert_called_once_with(storage_client_mock, ["Filter1"])
                    patch_in_use.assert_called_once_with(data['name'],
                                                         {'type': data['source']['type'], 'name': ''},
                                                         {'type': data['destination']['type'], 'name': ''}, info=True)
                patch_insert_tbl.assert_called_once_with('control_pipelines', insert_column)
        args, _ = patch_params.call_args_list[0]
        assert data == args[0]

    async def test_update(self, client):
        cpid = 1
        storage_result = {'id': cpid, 'name': 'Cp1', 'source': {'type': 'Any', 'name': ''}, 'destination':
            {'type': 'Broadcast', 'name': ''}, 'enabled': True, 'execution': 'Shared', 'filters': []}
        column_payload =  ('{"values": {"enabled": "t", "execution": "Shared", "stype": 3, "sname": "anonymous", '
                           '"dtype": 1, "dname": ""}, "where": {"column": "cpid", "condition": "=", "value": 1}}')
        payload = {'execution': 'Shared', 'source': {'type': 3, 'name': None}, 'destination': {'type': 1, 'name': None},
                   'filters': ["Filter1"], 'enabled': True}
        columns = {'enabled': 't', 'execution': 'Shared', 'stype': 3, 'sname': 'anonymous', 'dtype': 1, 'dname': ''}
        storage_client_mock = MagicMock(StorageClientAsync)
        rows_affected = {"response": "updated", "rows_affected": 1}
        update_pipeline = {'id': cpid, 'name': 'Cp1', 'source': {'type': 'API', 'name': ''}, 'destination':
            {'type': 'Any', 'name': ''}, 'enabled': True, 'execution': 'Shared', 'filters': []}
        filters = {"rows": [{"fname": "Filter1"}]}
        if sys.version_info >= (3, 8):
            rv = await mock_coro(storage_result)
            rv2 = await mock_coro(columns)
            rv3 = await mock_coro(rows_affected)
            rv4 = await mock_coro(None)
            rv5 = await mock_coro(update_pipeline)
            rv6 = await mock_coro(True)
            rv7 = await mock_coro(filters)
        else:
            rv = asyncio.ensure_future(mock_coro(storage_result))
            rv2 = asyncio.ensure_future(mock_coro(columns))
            rv3 = asyncio.ensure_future(mock_coro(rows_affected))
            rv4 = asyncio.ensure_future(mock_coro(None))
            rv5 = asyncio.ensure_future(mock_coro(update_pipeline))
            rv6 = asyncio.ensure_future(mock_coro(True))
            rv7 = asyncio.ensure_future(mock_coro(filters))
        with patch.object(pipeline, '_get_pipeline', side_effect=[rv, rv5]) as patch_pipeline:
            with patch.object(pipeline, '_check_parameters', return_value=rv2) as patch_params:
                with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                    with patch.object(storage_client_mock, 'update_tbl', return_value=rv3) as patch_update_tbl:
                        with patch.object(pipeline, '_check_filters', return_value=rv6) as patch_check_filter:
                            with patch.object(pipeline, '_get_table_column_by_value', return_value=rv7
                                              ) as patch_tbl_column:
                                with patch.object(pipeline, '_update_filters', return_value=rv4
                                                  ) as patch_update_filter:
                                    with patch.object(AuditLogger, '__init__', return_value=None):
                                        with patch.object(AuditLogger, 'information', return_value=rv4
                                                          ) as patch_audit:
                                            resp = await client.put('/fledge/control/pipeline/{}'.format(cpid),
                                                                    data=json.dumps(payload))
                                            assert 200 == resp.status
                                            result = await resp.text()
                                            json_response = json.loads(result)
                                            assert {"message": 'Control Pipeline with ID:<{}> has been '
                                                               'updated successfully.'.format(cpid)} == json_response
                                        patch_audit.assert_called_once_with(
                                            'CTPCH', {"pipeline": update_pipeline, "old_pipeline": storage_result})
                                patch_update_filter.assert_called_once_with(storage_client_mock, cpid, 'Cp1',
                                                                            ['Filter1'], ['Filter1'])
                            patch_tbl_column.assert_called_once_with('control_filters', 'cpid', str(cpid))
                        patch_check_filter.assert_called_once_with(storage_client_mock, ["Filter1"])
                    patch_update_tbl.assert_called_once_with('control_pipelines', column_payload)
            args, _ = patch_params.call_args_list[0]
            payload['old_pipeline_name'] = storage_result['name']
            assert payload == args[0]
        assert 2 == patch_pipeline.call_count

    async def test_bad_update(self, client):
        cpid = 1
        storage_result = {'id': cpid, 'name': 'Cp1', 'source': {'type': 'Any', 'name': ''}, 'destination':
            {'type': 'Broadcast', 'name': ''}, 'enabled': True, 'execution': 'Shared', 'filters': []}
        column_payload = ('{"values": {"enabled": "t", "execution": "Shared", "stype": 3, "sname": "anonymous", '
                          '"dtype": 1, "dname": ""}, "where": {"column": "cpid", "condition": "=", "value": 1}}')
        payload = {'execution': 'Shared', 'source': {'type': 3, 'name': None}, 'destination': {'type': 1, 'name': None},
                   'filters': ["Filter1"], 'enabled': True}
        columns = {'enabled': 't', 'execution': 'Shared', 'stype': 3, 'sname': 'anonymous', 'dtype': 1, 'dname': ''}
        storage_client_mock = MagicMock(StorageClientAsync)
        rows_affected = {"response": "updated", "rows_affected": 1}
        error_message = "Filters do not exist as per the given list ['Filter1']"
        if sys.version_info >= (3, 8):
            rv = await mock_coro(storage_result)
            rv2 = await mock_coro(columns)
            rv3 = await mock_coro(rows_affected)
            rv4 = await mock_coro(False)
        else:
            rv = asyncio.ensure_future(mock_coro(storage_result))
            rv2 = asyncio.ensure_future(mock_coro(columns))
            rv3 = asyncio.ensure_future(mock_coro(rows_affected))
            rv4 = asyncio.ensure_future(mock_coro(False))
        with patch.object(pipeline, '_get_pipeline', return_value=rv) as patch_pipeline:
            with patch.object(pipeline, '_check_parameters', return_value=rv2) as patch_params:
                with patch.object(connect, 'get_storage_async', return_value=storage_client_mock):
                    with patch.object(storage_client_mock, 'update_tbl', return_value=rv3) as patch_update_tbl:
                        with patch.object(pipeline, '_check_filters', return_value=rv4) as patch_check_filter:
                            resp = await client.put('/fledge/control/pipeline/{}'.format(cpid),
                                                    data=json.dumps(payload))
                            assert 400 == resp.status
                            assert error_message == resp.reason
                            result = await resp.text()
                            json_response = json.loads(result)
                            assert {"message": error_message} == json_response
                        patch_check_filter.assert_called_once_with(storage_client_mock, ["Filter1"])
                    patch_update_tbl.assert_called_once_with('control_pipelines', column_payload)
            args, _ = patch_params.call_args_list[0]
            payload['old_pipeline_name'] = storage_result['name']
            assert payload == args[0]
        patch_pipeline.assert_called_once_with(str(cpid))

    async def test__get_pipeline(self):
        cpid = 3
        result = {"rows": [{"cpid": cpid, "name": "CP-3", "stype": 1, "sname": "", "dtype": 5, "dname": "",
                            "enabled": "t", "execution": "Shared", "filters": ["Filter1"]}]}
        if sys.version_info >= (3, 8):
            rv = await mock_coro(result)
            rv2 = await mock_coro("Any")
            rv3 = await mock_coro({"rows": [{"fname": "Filter1"}]})
        else:
            rv = asyncio.ensure_future(mock_coro(result))
            rv2 = asyncio.ensure_future(mock_coro("Any"))
            rv3 = asyncio.ensure_future(mock_coro({"rows": [{"fname": "Filter1"}]}))
        with patch.object(pipeline, '_get_table_column_by_value', side_effect=[rv, rv3]):
            with patch.object(pipeline, '_get_lookup_value', return_value=rv2) as patch_lookup:
                res = await pipeline._get_pipeline(cpid, True)
                expected_rows = result["rows"][0]
                assert expected_rows['cpid'] == res['id']
                assert expected_rows['name'] == res['name']
                assert isinstance(res['source']['type'], str)
                assert expected_rows['sname'] == res['source']['name']
                assert isinstance(res['destination']['type'], str)
                assert expected_rows['dname'] == res['destination']['name']
                assert res['enabled'] is True
                assert expected_rows['execution'] == res['execution']
                assert expected_rows['filters'] == res['filters']
            assert 2 == patch_lookup.call_count
            args = patch_lookup.call_args_list
            arg, _ = args[0]
            assert ('source', result["rows"][0]['stype']) == arg
            arg, _ = args[1]
            assert ('destination', result["rows"][0]['dtype']) == arg

    async def test__remove_filters(self):
        filters = ["ctrl_cp_Scale"]
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        delete_result = {'response': 'deleted', 'rows_affected': 1}
        rv = await mock_coro(delete_result) if sys.version_info >= (3, 8) else asyncio.ensure_future(
            mock_coro(delete_result))
        with patch.object(storage_client_mock, 'delete_from_tbl', return_value=rv) as patch_delete_tbl:
            with patch.object(c_mgr, 'delete_category_and_children_recursively', return_value=rv) as patch_mgr:
                await pipeline._remove_filters(storage_client_mock, filters, 1)
            assert len(filters) * 2 == patch_mgr.call_count
            args = patch_mgr.call_args_list
            args1, _ = args[0]
            assert ('ctrl_cp_Scale',) == args1
            args2, _ = args[1]
            assert ('ctrl_cp_Scale',) == args2
        assert len(filters) * 2 == patch_delete_tbl.call_count
        args = patch_delete_tbl.call_args_list
        args1, _ = args[0]
        assert ('control_filters', '{"where": {"column": "cpid", "condition": "=", "value": 1, '
                                    '"and": {"column": "fname", "condition": "=", "value": "ctrl_cp_Scale"}}}') == args1
        args2, _ = args[1]
        assert ('filters', '{"where": {"column": "name", "condition": "=", "value": "ctrl_cp_Scale"}}') == args2

    @pytest.mark.parametrize("filters, is_exists", [
        (["REN1", "Scale"], True),
        (["Meta"], False)
    ])
    async def test__check_filters(self, filters, is_exists):
        res = {"rows": [{"name": "Scale"}, {"name": "REN1"}]}
        rv = await mock_coro(res) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(res))
        storage_client_mock = MagicMock(StorageClientAsync)
        with patch.object(storage_client_mock, 'query_tbl', return_value=rv) as patch_query_tbl:
            with patch.object(pipeline._logger, 'warning') as patch_logger:
                res = await pipeline._check_filters(storage_client_mock, filters)
                assert res is is_exists
            if not is_exists:
                patch_logger.assert_called_once_with("Filters do not exist as per the given {} payload.".format(filters))
            else:
                assert not patch_logger.called
        patch_query_tbl.assert_called_once_with("filters")

    async def test_insert_case_in_update_filters(self):
        filter_name = "Filter1"
        name = "Cp"
        storage_client_mock = MagicMock(StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        cat_info = {'write': {'default': '[{"order": 0, "service": "mod", "values": {"humidity": "12"}}]',
                              'description': 'Dispatcher write operation using automation script', 'type': 'string',
                              'value': '[{"order": 0, "service": "mod", "values": {"humidity": "12"}}]'}}
        insert_result = {"rows_affected": 1, "response": "inserted"}
        payload = {"cpid": 1, "forder": 1, "fname": "ctrl_{}_{}".format(name, filter_name)}
        if sys.version_info >= (3, 8):
            rv = await mock_coro(cat_info)
            rv2 = await mock_coro(insert_result)
        else:
            rv = asyncio.ensure_future(mock_coro(cat_info))
            rv2 = asyncio.ensure_future(mock_coro(insert_result))
        with patch.object(c_mgr, 'get_category_all_items', side_effect=[rv, rv]):
            with patch.object(c_mgr, 'create_category', return_value=rv) as patch_create_cat:
                with patch.object(storage_client_mock, 'insert_into_tbl', return_value=rv2) as patch_tbl:
                    with patch.object(c_mgr, 'create_child_category', return_value=rv) as patch_child_cat:
                        await pipeline._update_filters(storage_client_mock, 1, name, [filter_name])
                    patch_child_cat.assert_called_once_with("dispatcher",
                                                            ["ctrl_{}_{}".format(name, filter_name), filter_name])
                args = patch_tbl.call_args_list
                arg, _ = args[0]
                assert 'control_filters' == arg[0]
                assert payload == json.loads(arg[1])
            assert 1 == patch_create_cat.call_count

    async def test_update_case_in_update_filters(self):
        filter1= "Filter1"
        filter2 = "Filter2"
        name = "Cp"
        storage_client_mock = MagicMock(StorageClientAsync)
        payload = {"values": {"forder": 1}, "where": {"column": "fname", "condition": "=",
                                                      "value": "ctrl_{}_{}".format(name, filter2),
                                                      "and": {"column": "cpid", "condition": "=", "value": 1}}}
        rv = await mock_coro(None) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(None))
        with patch.object(storage_client_mock, 'update_tbl', return_value=rv) as patch_tbl:
            with patch.object(pipeline, '_remove_filters', return_value=rv) as patch_filters:
                await pipeline._update_filters(storage_client_mock, 1, name, [filter2], [filter1, filter2])
            patch_filters.assert_called_once_with(storage_client_mock, ['ctrl_{}_{}'.format(name, filter1)],
                                                  1, name)
        args = patch_tbl.call_args_list
        arg, _ = args[0]
        assert 'control_filters' == arg[0]
        assert payload == json.loads(arg[1])

    async def test_remove_case_in_update_filters(self):
        filter1= "Filter1"
        filter2 = "Filter2"
        name = "Cp"
        storage_client_mock = MagicMock(StorageClientAsync)
        rv = await mock_coro(None) if sys.version_info >= (3, 8) else asyncio.ensure_future(mock_coro(None))
        with patch.object(pipeline, '_remove_filters', return_value=rv) as patch_filters:
            await pipeline._update_filters(storage_client_mock, 1, name, [], [filter1, filter2])
        patch_filters.assert_called_once_with(
            storage_client_mock, ['ctrl_{}_{}'.format(name, filter1), 'ctrl_{}_{}'.format(
                name, filter2)], 1, name)

    @pytest.mark.parametrize("cf_data, cp_data, error_msg, func_call_count", [
        ({"rows": [1]}, {"rows": [1]}, "Filters are attached. Pipeline name cannot be changed.", 1),
        ({"rows": []}, {"rows": [1]}, "Cp pipeline already exists, name cannot be changed.", 2)
    ])
    async def test__check_unique_pipeline(self, cf_data, cp_data, error_msg, func_call_count):
        name = "Cp"
        cpid = 1
        if sys.version_info >= (3, 8):
            rv = await mock_coro(cf_data)
            rv2 = await mock_coro(cp_data)
        else:
            rv = asyncio.ensure_future(mock_coro(cf_data))
            rv2 = asyncio.ensure_future(mock_coro(cp_data))
        with patch.object(pipeline, '_get_table_column_by_value', side_effect=[rv, rv2]) as patch_tbl_col:
            with pytest.raises(Exception) as exc_info:
                await pipeline._check_unique_pipeline(name, cpid=cpid)
            assert exc_info.type is ValueError
            assert error_msg == exc_info.value.args[0]
        assert func_call_count == patch_tbl_col.call_count

