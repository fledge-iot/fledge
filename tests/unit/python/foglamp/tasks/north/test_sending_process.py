# -*- coding: utf-8 -*-
""" Unit tests for the North Sending Process """

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import logging
import sys
import time
from unittest.mock import patch, MagicMock, ANY

import pytest

import foglamp.tasks.north.sending_process as sp_module
from foglamp.common.audit_logger import AuditLogger
from foglamp.common.storage_client.storage_client import StorageClientAsync, ReadingsStorageClientAsync
from foglamp.tasks.north.sending_process import SendingProcess

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


pytestmark = pytest.mark.asyncio

STREAM_ID = 1

@asyncio.coroutine
def mock_coro(*args, **kwargs):
    if len(args) > 0:
        return args[0]
    else:
        return ""


async def mock_async_call():
    """ mocks a generic async function """
    return True


async def mock_audit_failure():
    """ mocks audit.failure """

    return True


@pytest.mark.asyncio
@pytest.fixture
def fixture_sp(event_loop):
    """"  Configures the sending process instance for the tests """
    
    with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
        sp = SendingProcess()

    SendingProcess._logger = MagicMock(spec=logging)

    sp._logger = MagicMock(spec=logging)
    sp._audit = MagicMock(spec=AuditLogger)

    sp._config_from_manager = {
        'applyFilter': {'value': "FALSE"}
    }

    sp._task_fetch_data_run = True
    sp._task_send_data_run = True

    sp._task_fetch_data_sem = asyncio.Semaphore(0)
    sp._task_send_data_sem = asyncio.Semaphore(0)
    
    return sp


@pytest.mark.parametrize(
    "p_data, "
    "expected_data",
    [
        ("2018-05-28 16:56:55",              "2018-05-28 16:56:55.000000+00"),
        ("2018-05-28 13:42:28.8",            "2018-05-28 13:42:28.800000+00"),
        ("2018-05-28 13:42:28.84",           "2018-05-28 13:42:28.840000+00"),
        ("2018-05-28 13:42:28.840000",       "2018-05-28 13:42:28.840000+00"),

        ("2018-03-22 17:17:17.166347",       "2018-03-22 17:17:17.166347+00"),

        ("2018-03-22 17:17:17.166347+00",    "2018-03-22 17:17:17.166347+00"),
        ("2018-03-22 17:17:17.166347+00:00", "2018-03-22 17:17:17.166347+00"),
        ("2018-03-22 17:17:17.166347+02:00", "2018-03-22 17:17:17.166347+00"),
        ("2018-03-22 17:17:17.166347+00:02", "2018-03-22 17:17:17.166347+00"),
        ("2018-03-22 17:17:17.166347+02:02", "2018-03-22 17:17:17.166347+00"),

        ("2018-03-22 17:17:17.166347-00",    "2018-03-22 17:17:17.166347+00"),
        ("2018-03-22 17:17:17.166347-00:00", "2018-03-22 17:17:17.166347+00"),
        ("2018-03-22 17:17:17.166347-02:00", "2018-03-22 17:17:17.166347+00"),
        ("2018-03-22 17:17:17.166347-00:02", "2018-03-22 17:17:17.166347+00"),
        ("2018-03-22 17:17:17.166347-02:02", "2018-03-22 17:17:17.166347+00"),

    ]
)
async def test_apply_date_format(p_data, expected_data):

    assert expected_data == sp_module.apply_date_format(p_data)


@pytest.mark.parametrize(
    "p_parameter, "
    "expected_param_mgt_name, "
    "expected_param_mgt_port, "
    "expected_param_mgt_address, "
    "expected_stream_id, "
    "expected_log_performance, "
    "expected_log_debug_level , "
    "expected_execution",
    [
        # Bad cases
        (
            ["", "--name", "SEND_PR1"],
            "",  "", "", 1, False, 0,
            "exception"
        ),
        (
            ["", "--name", "SEND_PR1", "--port", "0001"],
            "", "", "", 1, False, 0,
            "exception"
        ),
        (
            ["", "--name", "SEND_PR1", "--port", "0001", "--address", "127.0.0.0"],
            "", "", "", 1, False, 0,
            "exception"
        ),
        # stream_id must be an integer
        (
            ["", "--name", "SEND_PR1", "--port", "0001", "--address", "127.0.0.0", "--stream_id", "x"],
            "", "", "", 1, False, 0,
            "exception"
        ),

        # Good cases
        (
            # p_parameter
            ["", "--name", "SEND_PR1", "--port", "0001", "--address", "127.0.0.0", "--stream_id", "1"],

            # expected_param_mgt_name
            "SEND_PR1",
            # expected_param_mgt_port
            "0001",
            # expected_param_mgt_address
            "127.0.0.0",
            # expected_stream_id
            1,
            # expected_log_performance
            False,
            # expected_log_debug_level
            0,
            # expected_execution
            "good"
        ),

        (
            # Case - --performance_log
            # p_parameter
            ["", "--name", "SEND_PR1", "--port", "0001", "--address", "127.0.0.0", "--stream_id", "1",
             "--performance_log", "1"],

            # expected_param_mgt_name
            "SEND_PR1",
            # expected_param_mgt_port
            "0001",
            # expected_param_mgt_address
            "127.0.0.0",
            # expected_stream_id
            1,
            # expected_log_performance
            True,
            # expected_log_debug_level
            0,
            # expected_execution
            "good"
        ),

        (
            # Case - --debug_level
            # p_parameter
            ["", "--name", "SEND_PR1", "--port", "0001", "--address", "127.0.0.0", "--stream_id", "1",
             "--performance_log", "1", "--debug_level", "3"],

            # expected_param_mgt_name
            "SEND_PR1",
            # expected_param_mgt_port
            "0001",
            # expected_param_mgt_address
            "127.0.0.0",
            # expected_stream_id
            1,
            # expected_log_performance
            True,
            # expected_log_debug_level
            3,
            # expected_execution
            "good"
        ),
    ]
)
async def test_handling_input_parameters(
                                    p_parameter,
                                    expected_param_mgt_name,
                                    expected_param_mgt_port,
                                    expected_param_mgt_address,
                                    expected_stream_id,
                                    expected_log_performance,
                                    expected_log_debug_level,
                                    expected_execution):
    """ Tests the handing of input parameters of the Sending process """

    sys.argv = p_parameter

    sp_module._LOGGER = MagicMock(spec=logging)

    if expected_execution == "good":

        param_mgt_name, \
            param_mgt_port, \
            param_mgt_address, \
            stream_id, \
            log_performance, \
            log_debug_level \
            = sp_module.handling_input_parameters()

        # noinspection PyProtectedMember
        assert not sp_module._LOGGER.error.called

        assert param_mgt_name == expected_param_mgt_name
        assert param_mgt_port == expected_param_mgt_port
        assert param_mgt_address == expected_param_mgt_address
        assert stream_id == expected_stream_id
        assert log_performance == expected_log_performance
        assert log_debug_level == expected_log_debug_level

    elif expected_execution == "exception":

        with pytest.raises(sp_module.InvalidCommandLineParameters):
            sp_module.handling_input_parameters()

        # noinspection PyProtectedMember
        assert sp_module._LOGGER.error.called


# noinspection PyUnresolvedReferences
@pytest.allure.feature("unit")
@pytest.allure.story("tasks", "north")
class TestSendingProcess:
    """Unit tests for the sending_process.py"""

    @pytest.mark.parametrize(
        "p_stream_id, "
        "p_rows, "
        "expected_stream_id_valid, "
        "expected_execution",
        [
            # Good cases
            (
                # p_stream_id
                1,
                # p_rows
                {
                    "rows":
                    [
                      {"active": "t"}
                    ]
                },
                # expected_stream_id_valid = True, it is a valid stream id
                True,
                # expected_execution
                "good"
            ),

            (
                # p_stream_id
                1,
                # p_rows
                {
                    "rows":
                        [
                            {"active": "f"}
                        ]
                },
                # expected_stream_id_valid = True, it is a valid stream id
                False,
                # expected_execution
                "good"
            ),

            # Bad cases
            # 0 rows
            (
                # p_stream_id
                1,
                # p_rows
                {
                    "rows":
                        [
                        ]
                },
                # expected_stream_id_valid = True, it is a valid stream id
                False,
                # expected_execution
                "exception"
            ),
            # Multiple rows
            (
                    # p_stream_id
                    1,
                    # p_rows
                    {
                        "rows":
                            [
                                {"active": "t"},
                                {"active": "f"}
                            ]
                    },
                    # expected_stream_id_valid = True, it is a valid stream id
                    False,
                    # expected_execution
                    "exception"
            ),

        ]
    )
    async def test_is_stream_id_valid(self,
                                p_stream_id,
                                p_rows,
                                expected_stream_id_valid,
                                expected_execution,
                                event_loop):
        """ Unit tests for - _is_stream_id_valid """

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        SendingProcess._logger = MagicMock(spec=logging)
        sp._logger = MagicMock(spec=logging)
        sp._storage_async = MagicMock(spec=StorageClientAsync)

        if expected_execution == "good":

            with patch.object(sp._storage_async, 'query_tbl', return_value=mock_coro(p_rows)):
                generate_stream_id = await sp._is_stream_id_valid(p_stream_id)

            # noinspection PyProtectedMember
            assert not SendingProcess._logger.error.called

            assert generate_stream_id == expected_stream_id_valid

        elif expected_execution == "exception":

            with patch.object(sp._storage_async, 'query_tbl', side_effect=ValueError):
                with pytest.raises(ValueError):
                    await sp._is_stream_id_valid(p_stream_id)

            # noinspection PyProtectedMember
            assert SendingProcess._logger.error.called

    @pytest.mark.parametrize("plugin_file, plugin_type, plugin_name, expected_result", [
        ("omf", "north", "OMF North", True),
        ("omf", "north", "Empty North Plugin", False),
        ("omf", "south", "OMF North", False)
    ])
    async def test_is_north_valid(self,  plugin_file, plugin_type, plugin_name, expected_result, event_loop):
        """Tests the possible cases of the function is_north_valid """

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._config['north'] = plugin_file
        sp._plugin_load()

        sp._plugin_info = sp._plugin.plugin_info()
        sp._plugin_info['type'] = plugin_type
        sp._plugin_info['name'] = plugin_name

        assert sp._is_north_valid() == expected_result

    @pytest.mark.asyncio
    async def test_load_data_into_memory(self,
                                         loop):
        """ Unit test for - test_load_data_into_memory"""

        async def mock_coroutine():
            """" mock_coroutine """
            return True

        # Checks the Readings handling
        with patch.object(asyncio, 'get_event_loop', return_value=loop):
            sp = SendingProcess()

        # Tests - READINGS
        sp._config['source'] = sp._DATA_SOURCE_READINGS

        with patch.object(sp, '_load_data_into_memory_readings', return_value=mock_coroutine()) \
                as mocked_load_data_into_memory_readings:

            await sp._load_data_into_memory(5)
            assert mocked_load_data_into_memory_readings.called

        # Tests - STATISTICS
        sp._config['source'] = sp._DATA_SOURCE_STATISTICS

        with patch.object(sp, '_load_data_into_memory_statistics', return_value=mock_coro(True)) \
                as mocked_load_data_into_memory_statistics:

            await  sp._load_data_into_memory(5)
            assert mocked_load_data_into_memory_statistics.called

        # Tests - AUDIT
        sp._config['source'] = sp._DATA_SOURCE_AUDIT

        with patch.object(sp, '_load_data_into_memory_audit', return_value=mock_coro(True)) \
                as mocked_load_data_into_memory_audit:

            await  sp._load_data_into_memory(5)
            assert mocked_load_data_into_memory_audit.called

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "p_rows, "
        "expected_rows, ",
        [
            # Case 1: Base case and Timezone added
            (
                # p_rows
                {
                    "rows": [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 11, "temperature": 38},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ]
                },
                # expected_rows,
                # NOTE:
                #    Time generated with UTC timezone
                [
                    {
                        "id": 1,
                        "asset_code": "test_asset_code",
                        "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                        "reading": {"humidity": 11, "temperature": 38},
                        "user_ts": "16/04/2018 16:32:55.000000+00"
                    },
                ]

            )
        ]
    )
    async def test_load_data_into_memory_readings(self,
                                            event_loop,
                                            p_rows,
                                            expected_rows):
        """Test _load_data_into_memory handling and transformations for the readings """

        async def mock_coroutine():
            """" mock_coroutine """
            return p_rows

        # Checks the Readings handling
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._config['source'] = sp._DATA_SOURCE_READINGS

        sp._readings = MagicMock(spec=ReadingsStorageClientAsync)

        # Checks the transformations and especially the adding of the UTC timezone
        with patch.object(sp._readings, 'fetch', return_value=mock_coroutine()):

            generated_rows = await sp._load_data_into_memory_readings(5)

            assert len(generated_rows) == 1
            assert generated_rows == expected_rows

    @pytest.mark.parametrize(
        "p_rows, "
        "expected_rows, ",
        [
            # Case 1:
            # NOTE:
            #    Time generated with UTC timezone

            (
                # p_rows
                [
                    {
                        "id": 1,
                        "asset_code": "test_asset_code",
                        "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                        "reading": {"humidity": 11, "temperature": 38},
                        "user_ts": "16/04/2018 16:32:55"
                    },
                ],
                # expected_rows,
                [
                    {
                        "id": 1,
                        "asset_code": "test_asset_code",
                        "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                        "reading": {"humidity": 11, "temperature": 38},
                        "user_ts": "16/04/2018 16:32:55.000000+00"
                    },
                ]

            ),

            # Case 2: "180.2" to float 180.2
            (
                    # p_rows
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": "180.2"},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ],
                    # expected_rows,
                    # NOTE:
                    #    Time generated with UTC timezone
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 180.2},
                            "user_ts": "16/04/2018 16:32:55.000000+00"
                        },
                    ]

            )
        ]
    )
    async def test_transform_in_memory_data_readings(self,
                                               event_loop,
                                               p_rows,
                                               expected_rows):
        """ Unit test for - _transform_in_memory_data_readings"""

        # Checks the Readings handling
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        # Checks the transformations and especially the adding of the UTC timezone
        generated_rows = sp._transform_in_memory_data_readings(p_rows)

        assert len(generated_rows) == 1
        assert generated_rows == expected_rows

    @pytest.mark.parametrize(
        "p_rows, "
        "expected_rows, ",
        [
            # Case 1:
            #    fields mapping,
            #       key->asset_code
            #    Timezone added
            #    reading format handling
            #
            # Note :
            #    read_key is not handled
            #    Time generated with UTC timezone
            (
                # p_rows
                {
                    "rows": [
                        {
                            "id": 1,
                            "key": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "value": 20,
                            "ts": "16/04/2018 16:32:55"
                        },
                    ]
                },
                # expected_rows,
                [
                    {
                        "id": 1,
                        "asset_code": "test_asset_code",
                        "reading": {"value": 20},
                        "user_ts": "16/04/2018 16:32:55.000000+00"
                    },
                ]

            ),

            # Case 2: key is having spaces
            (
                    # p_rows
                    {
                        "rows": [
                            {
                                "id": 1,
                                "key": " test_asset_code ",
                                "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                                "value": 21,
                                "ts": "16/04/2018 16:32:55"
                            },
                        ]
                    },
                    # expected_rows,
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "reading": {"value": 21},
                            "user_ts": "16/04/2018 16:32:55.000000+00"
                        },
                    ]

            )

        ]
    )
    async def test_load_data_into_memory_statistics(self,
                                              event_loop,
                                              p_rows,
                                              expected_rows):
        """Test _load_data_into_memory handling and transformations for the statistics """

        # Checks the Statistics handling
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._config['source'] = sp._DATA_SOURCE_STATISTICS

        sp._storage_async = MagicMock(spec=StorageClientAsync)

        # Checks the transformations for the Statistics especially for the 'reading' field and the fields naming/mapping
        with patch.object(sp._storage_async, 'query_tbl_with_payload', return_value=mock_coro(p_rows)):

            generated_rows = await sp._load_data_into_memory_statistics(5)

            assert len(generated_rows) == 1
            assert generated_rows == expected_rows

    @pytest.mark.parametrize(
        "p_rows, "
        "expected_rows, ",
        [
            # Case 1:
            #    fields mapping,
            #       key->asset_code
            #    Timezone added
            #    reading format handling
            #
            # Note :
            #    read_key is not handled
            #    Time generated with UTC timezone
            (
                # p_rows
                [
                        {
                            "id": 1,
                            "key": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "value": 20,
                            "ts": "16/04/2018 16:32:55"
                        },
                ],
                # expected_rows,
                [
                    {
                        "id": 1,
                        "asset_code": "test_asset_code",
                        "reading": {"value": 20},
                        "user_ts": "16/04/2018 16:32:55.000000+00"
                    },
                ]

            ),

            # Case 2: key is having spaces
            (
                    # p_rows
                    [
                        {
                            "id": 1,
                            "key": " test_asset_code ",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "value": 21,
                            "ts": "16/04/2018 16:32:55"
                        },
                    ],
                    # expected_rows,
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "reading": {"value": 21},
                            "user_ts": "16/04/2018 16:32:55.000000+00"
                        },
                    ]

            )

        ]
    )
    async def test_transform_in_memory_data_statistics(self,
                                                 event_loop,
                                                 p_rows,
                                                 expected_rows):
        """ Unit test for - _transform_in_memory_data_statistics"""

        # Checks the Statistics handling
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._storage_async = MagicMock(spec=StorageClientAsync)
        with patch.object(sp._storage_async, 'query_tbl_with_payload', return_value=mock_coro()):

            # Checks the transformations for the Statistics especially for the 'reading' field and the fields naming/mapping
            generated_rows = sp._transform_in_memory_data_statistics(p_rows)

            assert len(generated_rows) == 1
            assert generated_rows == expected_rows

    async def test_load_data_into_memory_audit(self,
                                         event_loop
                                         ):
        """ Unit test for - _load_data_into_memory_audit, NB the function is currently not implemented """

        # Checks the Statistics handling
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._config['source'] = sp._DATA_SOURCE_AUDIT
        sp._storage_async = MagicMock(spec=StorageClientAsync)

        generated_rows = await sp._load_data_into_memory_audit(5)

        assert len(generated_rows) == 0
        assert generated_rows == ""

    async def test_last_object_id_read(self, event_loop):
        """Tests the possible cases for the function last_object_id_read """

        async def mock_query_tbl_row_1():
            """Mocks the query_tbl function of the StorageClientAsync object - good case"""

            rows = {"rows": [{"last_object": 10}]}
            return rows

        async def mock_query_tbl_row_0():
            """Mocks the query_tbl function of the StorageClientAsync object - base case"""

            rows = {"rows": []}
            return rows

        async def mock_query_tbl_row_2():
            """Mocks the query_tbl function of the StorageClientAsync object - base case"""

            rows = {"rows": [{"last_object": 10}, {"last_object": 11}]}
            return rows

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._storage_async = MagicMock(spec=StorageClientAsync)

        # Good Case
        with patch.object(sp._storage_async, 'query_tbl', return_value=mock_query_tbl_row_1()) as sp_mocked:
            position = await sp._last_object_id_read(1)
            sp_mocked.assert_called_once_with('streams', 'id=1')
            assert position == 10

        # Bad cases
        sp._logger.error = MagicMock()
        with patch.object(sp._storage_async, 'query_tbl', return_value=mock_query_tbl_row_0()):
            # noinspection PyBroadException
            try:
                await sp._last_object_id_read(1)
            except Exception:
                pass

            sp._logger.error.assert_called_once_with(sp_module._MESSAGES_LIST["e000019"])

        sp._logger.error = MagicMock()
        with patch.object(sp._storage_async, 'query_tbl', return_value=mock_query_tbl_row_2()):
            # noinspection PyBroadException
            try:
                await sp._last_object_id_read(1)
            except Exception:
                pass

            sp._logger.error.assert_called_once_with(sp_module._MESSAGES_LIST["e000019"])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "p_duration, "
        "p_sleep_interval, "
        "p_signal_received, "  # simulates the termination signal
        "expected_time, "
        "tolerance ",
        [
            # p_duration - p_sleep_interval  - p_signal_received - expected_time - tolerance
            (10,           1,                 False,              10,            5),
            (60,          1,                  True,               0,             5),

        ]
    )
    async def test_send_data_good(
                            self,
                            event_loop,
                            p_duration,
                            p_sleep_interval,
                            p_signal_received,
                            expected_time,
                            tolerance):
        """ Unit tests - send_data """

        async def mock_task():
            """ Dummy async task """
            pass

            return True

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._logger = MagicMock(spec=logging)

        # Configures properly the SendingProcess
        sp._config = {
            'duration': p_duration,
            'sleepInterval': p_sleep_interval,
            'memory_buffer_size': 1000
        }

        # Simulates the reception of the termination signal
        if p_signal_received:
            SendingProcess._stop_execution = True
        else:
            SendingProcess._stop_execution = False

        # Force tasks immediately termination
        sp._task_fetch_data_run = False
        sp._task_send_data_run = False

        # Start time track
        start_time = time.time()

        with patch.object(sp, '_last_object_id_read', return_value=0):
            await sp.send_data(STREAM_ID)

        # It considers a reasonable tolerance
        elapsed_seconds = time.time() - start_time
        assert expected_time <= elapsed_seconds <= (expected_time + tolerance)

    @pytest.mark.parametrize(
        "p_rows, "                 # GIVEN, information retrieve from the storage layer
        "p_num_element_to_fetch, " 
        "p_buffer_size, "          # size of the in memory buffer        
        "expected_buffer ",        # THEN, expected in memory buffer loaded by the _task_fetch_data function
        [
            (
                # p_rows
                [
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 10, "temperature": 101},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                        {
                            "id": 2,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 20, "temperature": 201},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ],
                    [
                        {
                            "id": 3,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 30, "temperature": 301},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ],
                    [
                        {
                            "id": 4,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 40, "temperature": 401},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                        {
                            "id": 5,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 50, "temperature": 501},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                        {
                            "id": 6,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 60, "temperature": 601},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ]

                ],
                # p_num_element_to_fetch
                3,
                # p_buffer_size
                3,

                #  expected_buffer - 2 dimensions list
                [
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 10, "temperature": 101},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                        {
                            "id": 2,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 20, "temperature": 201},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ],
                    [
                        {
                            "id": 3,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 30, "temperature": 301},
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ],
                    [
                        {
                            "id": 4,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 40, "temperature": 401},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                        {
                            "id": 5,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 50, "temperature": 501},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                        {
                            "id": 6,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 60, "temperature": 601},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ]
                ]

            )
        ]
    )

    async def test_task_fetch_data_fill_buffer(
                                                self,
                                                event_loop,
                                                p_rows,
                                                p_buffer_size,
                                                p_num_element_to_fetch,
                                                expected_buffer):
        """ Unit tests - _task_fetch_data - fill the memory buffer

            Checks if the fetch task/function properly fills the in memory buffer
            in relation to defined set of inputs
        """

        async def retrieve_rows(idx):
            """ mock rows retrieval from the storage layer """
            return p_rows[idx]

        # GIVEN
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._logger = MagicMock(spec=logging)

        # Configures properly the SendingProcess
        sp._config = {
            'memory_buffer_size': p_buffer_size
        }

        sp._config_from_manager = {
            'applyFilter': {'value': "FALSE"}
        }

        sp._task_fetch_data_run = True

        sp._task_fetch_data_sem = asyncio.Semaphore(0)
        sp._task_send_data_sem = asyncio.Semaphore(0)

        # Prepares the in memory buffer for the fetch/send operations
        sp._memory_buffer = [None for x in range(sp._config['memory_buffer_size'])]

        # WHEN
        with patch.object(sp, '_last_object_id_read', return_value=mock_coro(0)):

            with patch.object(sp, '_load_data_into_memory',
                              side_effect=[asyncio.ensure_future(retrieve_rows(x)) for x in range(0, p_num_element_to_fetch)]):

                task_id = asyncio.ensure_future(sp._task_fetch_data(STREAM_ID))

                # Lets the _task_fetch_data to run for a while
                await asyncio.sleep(3)

                # Tear down
                sp._task_fetch_data_run = False
                sp._task_fetch_data_sem.release()
                sp._task_send_data_sem.release()

                await task_id

        # THEN
        assert sp._memory_buffer == expected_buffer

    @pytest.mark.parametrize(
        "p_rows, "            # GIVEN, information retrieve from the storage layer
        "p_num_element_to_fetch, " 
        "p_buffer_size, "     # size of the in memory buffer        
        "expected_buffer ",   # THEN, expected in memory buffer loaded by the _task_fetch_data function
        [
            (
                # p_rows
                [
                    # Step 1
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 10, "temperature": 101},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                        {
                            "id": 2,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 20, "temperature": 201},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ],
                    [
                        {
                            "id": 3,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 30, "temperature": 301},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ],
                    [
                        {
                            "id": 4,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 40, "temperature": 401},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                        {
                            "id": 5,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 50, "temperature": 501},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                        {
                            "id": 6,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 60, "temperature": 601},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ],

                    # Step 2
                    [
                        {
                            "id": 10,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 100, "temperature": 1001},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ]

                ],
                # p_num_element_to_fetch
                4,
                # p_buffer_size
                3,

                #  expected_buffer - 2 dimensions list
                [
                    # Loaded at first step 2
                    [
                        {
                            "id": 10,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 100, "temperature": 1001},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ],
                    # Loaded at first step 1
                    [
                        {
                            "id": 3,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 30, "temperature": 301},
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ],
                    [
                        {
                            "id": 4,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 40, "temperature": 401},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                        {
                            "id": 5,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 50, "temperature": 501},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                        {
                            "id": 6,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 60, "temperature": 601},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ]
                ]

            )
        ]
    )
    @pytest.mark.asyncio
    async def test_task_fetch_data_cycle_buffer(
                                                self,
                                                event_loop,
                                                p_rows,
                                                p_num_element_to_fetch,
                                                p_buffer_size,
                                                expected_buffer):
        """ Unit tests - _task_fetch_data - add a new element after filling the memory buffer"""

        async def retrieve_rows(idx):
            """ mock rows retrieval from the storage layer - used for the first fill """
            return p_rows[idx]

        # GIVEN
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._logger = MagicMock(spec=logging)

        # Configures properly the SendingProcess
        sp._config = {
            'memory_buffer_size': p_buffer_size
        }

        sp._config_from_manager = {
            'applyFilter': {'value': "FALSE"}
        }

        sp._task_fetch_data_run = True

        sp._task_fetch_data_sem = asyncio.Semaphore(0)
        sp._task_send_data_sem = asyncio.Semaphore(0)

        # Prepares the in memory buffer for the fetch/send operations
        sp._memory_buffer = [None for x in range(sp._config['memory_buffer_size'])]

        # WHEN
        # Starts the fetch 'task'
        with patch.object(sp, '_last_object_id_read', return_value=mock_coro(0)):
            with patch.object(sp, '_load_data_into_memory',
                              side_effect=[asyncio.ensure_future(retrieve_rows(x)) for x in range(0, p_num_element_to_fetch)]):

                task_id = asyncio.ensure_future(sp._task_fetch_data(STREAM_ID))

                # Lets the _task_fetch_data to run for a while, to fill the in memory buffer
                await asyncio.sleep(3)

                # Simulates the sent operation - so another block is loaded
                sp._memory_buffer[0] = None

                # Lets the fetch task to restart
                sp._task_send_data_sem.release()

                # Lets the _task_fetch_data to run for a while
                await asyncio.sleep(3)

                # Tear down
                sp._task_fetch_data_run = False
                sp._task_send_data_sem.release()

                await task_id

        # THEN
        assert sp._memory_buffer == expected_buffer

    @pytest.mark.parametrize(
        "p_rows, "            # GIVEN, information retrieve from the storage layer
        "p_num_element_to_fetch, " 
        "p_buffer_size, "     # size of the in memory buffer        
        "expected_buffer ",   # THEN, expected in memory buffer loaded by the _task_fetch_data function
        [
            (
                # p_rows
                [
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 10, "temperature": 101},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                        {
                            "id": 2,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 20, "temperature": 201},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ],
                    [
                        {
                            "id": 3,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 30, "temperature": 301},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ]
                ],
                # p_num_element_to_fetch
                2,
                # p_buffer_size
                3,

                #  expected_buffer - 2 dimensions list
                [
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 10, "temperature": 101},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                        {
                            "id": 2,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 20, "temperature": 201},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ],
                    [
                        {
                            "id": 3,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {"humidity": 30, "temperature": 301},
                            "user_ts": "16/04/2018 16:32:55"
                        },
                    ],
                    None

                ]

            )
        ]
    )
    @pytest.mark.asyncio
    async def test_task_fetch_data_error(
                                            self,
                                            event_loop,
                                            p_rows,
                                            p_num_element_to_fetch,
                                            p_buffer_size,
                                            expected_buffer):
        """ Unit tests - _task_fetch_data - simulates and error while fetching """

        async def mock_retrieve_rows(idx):
            """ mock rows retrieval from the storage layer - used for the first fill """
            return p_rows[idx]

        # GIVEN
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._logger = MagicMock(spec=logging)
        sp._audit = MagicMock(spec=AuditLogger)
        SendingProcess._logger = MagicMock(spec=logging)

        # Configures properly the SendingProcess
        sp._config = {
            'memory_buffer_size': p_buffer_size
        }

        sp._config_from_manager = {
            'applyFilter': {'value': "FALSE"}
        }

        sp._task_fetch_data_run = True

        sp._task_fetch_data_sem = asyncio.Semaphore(0)
        sp._task_send_data_sem = asyncio.Semaphore(0)

        # Prepares the in memory buffer for the fetch/send operations
        sp._memory_buffer = [None for x in range(sp._config['memory_buffer_size'])]

        # WHEN - Starts the fetch 'task'
        with patch.object(sp, '_last_object_id_read', return_value=mock_coro(0)):
            with patch.object(SendingProcess._logger, 'error') as patched_logger:
                with patch.object(sp._audit, 'failure', return_value=mock_audit_failure()) as patched_audit:
                    with patch.object(sp, '_load_data_into_memory',
                                      side_effect=[asyncio.ensure_future(mock_retrieve_rows(x)) for x in range(0, p_num_element_to_fetch)]):

                        # to mask - cannot reuse already awaited coroutine
                        with pytest.raises(RuntimeError):
                            task_id = asyncio.ensure_future(sp._task_fetch_data(STREAM_ID))

                            # Lets the _task_fetch_data to run for a while
                            await asyncio.sleep(3)

                            # Tear down
                            sp._task_fetch_data_run = False
                            sp._task_send_data_sem.release()

                            await task_id

        # THEN - Checks log and audit are called in case of en error and the in memory buffer is as expected
        assert patched_logger.called
        assert patched_audit.called
        patched_audit.assert_called_with(SendingProcess._AUDIT_CODE, ANY)

        assert sp._memory_buffer == expected_buffer


    @pytest.mark.parametrize(
        "p_rows, "                  # GIVEN, information retrieve from the storage layer
        "p_num_element_to_fetch, " 
        "p_buffer_size, "           # size of the in memory buffer
        "p_jqfilter, "              # JQ filter to apply
        "expected_buffer ",         # THEN, expected in memory buffer loaded by the _task_fetch_data function
        [
            (
                # p_rows
                [
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {
                                "humidity": 11, "temperature": 38
                            },
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ],
                    [
                        {
                            "id": 2,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {
                                "humidity": 20, "temperature": 201
                            },
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ],
                    [
                        {
                            "id": 3,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {
                                "humidity": 30, "temperature": 301
                            },
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ]
                ],
                # p_num_element_to_fetch
                3,
                # p_buffer_size
                3,
                # p_jqfilter
                "(.[]|.reading|.addedField)=512",

                #  expected_buffer - 2 dimensions list
                [
                    [
                        {
                            'read_key': 'ef6e1368-4182-11e8-842f-0ed5f89f718b',
                            'id': 1,
                            'reading': {
                                'humidity': 11,
                                'temperature': 38,
                                'addedField': 512
                            },
                            'asset_code': 'test_asset_code',
                            'user_ts': '16/04/2018 16:32:55'
                        }
                    ],
                    [
                        {
                            'read_key': 'ef6e1368-4182-11e8-842f-0ed5f89f718b',
                            'id': 2,
                            'reading': {
                                'humidity': 20,
                                'temperature': 201,
                                'addedField': 512
                            },
                            'asset_code': 'test_asset_code',
                            'user_ts': '16/04/2018 16:32:55'
                        }
                    ],
                    [
                        {
                            'read_key': 'ef6e1368-4182-11e8-842f-0ed5f89f718b',
                            'id': 3,
                            'reading': {
                                'humidity': 30,
                                'temperature': 301,
                                'addedField': 512
                            },
                            'asset_code': 'test_asset_code',
                            'user_ts': '16/04/2018 16:32:55'
                        }
                    ],
                ]

            )
        ]
    )
    @pytest.mark.asyncio
    async def test_task_fetch_data_jqfilter(
                                            self,
                                            event_loop,
                                            p_rows,
                                            p_num_element_to_fetch,
                                            p_buffer_size,
                                            p_jqfilter,
                                            expected_buffer):
        """ Unit tests - _task_fetch_data - tests JQFilter functionalities """

        async def mock_retrieve_rows(idx):
            """ mock rows retrieval from the storage layer"""
            return p_rows[idx]

        # GIVEN
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._logger = MagicMock(spec=logging)
        SendingProcess._logger = MagicMock(spec=logging)
        sp._audit = MagicMock(spec=AuditLogger)

        # Configures properly the SendingProcess, enabling JQFilter
        sp._config = {
            'memory_buffer_size': p_buffer_size
        }

        sp._config_from_manager = {
            "applyFilter": {"value": "TRUE"},
            "filterRule": {"value": p_jqfilter}
        }

        sp._task_fetch_data_run = True

        sp._task_fetch_data_sem = asyncio.Semaphore(0)
        sp._task_send_data_sem = asyncio.Semaphore(0)

        # Prepares the in memory buffer for the fetch/send operations
        sp._memory_buffer = [None for x in range(sp._config['memory_buffer_size'])]

        # WHEN - Starts the fetch 'task'
        with patch.object(sp, '_last_object_id_read', return_value=mock_coro(0)):
            with patch.object(sp, '_load_data_into_memory',
                              side_effect=[asyncio.ensure_future(mock_retrieve_rows(x)) for x in range(0, p_num_element_to_fetch)]):

                task_id = asyncio.ensure_future(sp._task_fetch_data(STREAM_ID))

                # Lets the _task_fetch_data to run for a while
                await asyncio.sleep(3)

                # Tear down
                sp._task_fetch_data_run = False
                sp._task_send_data_sem.release()

                await task_id

        assert sp._memory_buffer == expected_buffer

    @pytest.mark.parametrize(
        "p_rows, "                  # GIVEN, information available in the in memory buffer
        "p_buffer_size, "           # size of the in memory buffer
        "p_send_result, "           # Values returned by the _plugin.plugin_send
        "expected_num_sent, "       # THEN, expected elements sent
        "expected_buffer ",         # expected in memory buffer after the _task_send_data operations
        [
            # Case 1
            (
                    # p_rows
                    [
                        [
                            {
                                "id": 1,
                                "asset_code": "test_asset_code",
                                "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                                "reading": {
                                    "humidity": 11, "temperature": 38
                                },
                                "user_ts": "16/04/2018 16:32:55"
                            }
                        ]
                    ],
                    # p_buffer_size
                    3,

                    # p_send_result
                    [
                        {
                            "data_sent": True,
                            "new_last_object_id": 1,
                            "num_sent": 1,
                        }
                    ],

                    # expected_num_sent
                    1,

                    #  expected_buffer - 2 dimensions list
                    [
                        None,
                        None,
                        None
                    ]

            ),

            # Case 2 - fills the buffer
            (
                # p_rows
                [
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {
                                "humidity": 11, "temperature": 38
                            },
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ],
                    [
                        {
                            "id": 2,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {
                                "humidity": 20, "temperature": 201
                            },
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ],
                    [
                        {
                            "id": 4,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {
                                "humidity": 30, "temperature": 301
                            },
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ]
                ],
                # p_buffer_size
                3,

                # p_send_result
                [
                    {
                        "data_sent": True,
                        "new_last_object_id": 1,
                        "num_sent": 1,
                     },
                    {
                        "data_sent": True,
                        "new_last_object_id": 2,
                        "num_sent": 1,
                    },
                    {
                        "data_sent": True,
                        "new_last_object_id": 4,
                        "num_sent": 1,
                    },

                ],

                # expected_num_sent
                3,

                #  expected_buffer - 2 dimensions list
                [
                    None,
                    None,
                    None
                ]

            ),
        ]
    )
    @pytest.mark.asyncio
    async def test_task_send_data_fill_buffer(
                                            self,
                                            event_loop,
                                            p_rows,
                                            p_buffer_size,
                                            p_send_result,
                                            expected_num_sent,
                                            expected_buffer):
        """ Unit tests - _task_send_data - send data without errors """

        async def mock_send_rows(x):
            """ mock the results of the sending operation """
            return p_send_result[x]["data_sent"], p_send_result[x]["new_last_object_id"], p_send_result[x]["num_sent"]

        # GIVEN
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._logger = MagicMock(spec=logging)
        SendingProcess._logger = MagicMock(spec=logging)
        sp._audit = MagicMock(spec=AuditLogger)

        # Configures properly the SendingProcess, enabling JQFilter
        sp._config = {
            'memory_buffer_size': p_buffer_size
        }

        sp._config_from_manager = {
            'applyFilter': {'value': "FALSE"}
        }

        sp._task_send_data_run = True

        sp._task_fetch_data_sem = asyncio.Semaphore(0)
        sp._task_send_data_sem = asyncio.Semaphore(0)

        # Allocates the in memory buffer
        sp._memory_buffer = [None for x in range(p_buffer_size)]

        # Fills the buffer
        for x in range(len(p_rows)):
            sp._memory_buffer[x] = p_rows[x]

        # WHEN - Starts the fetch 'task'
        with patch.object(sp, '_update_position_reached', return_value=mock_async_call()) \
                as patched_update_position_reached:

            with patch.object(sp._plugin, 'plugin_send',
                              side_effect=[asyncio.ensure_future(mock_send_rows(x)) for x in range(0, len(p_send_result))]):

                task_id = asyncio.ensure_future(sp._task_send_data(STREAM_ID))

                # Lets the _task_fetch_data to run for a while
                await asyncio.sleep(3)

                # Tear down
                sp._task_send_data_run = False
                sp._task_fetch_data_sem.release()

                await task_id

        expected_new_last_object_id = p_send_result[len(p_send_result) - 1]["new_last_object_id"]

        assert sp._memory_buffer == expected_buffer
        patched_update_position_reached.assert_called_with(STREAM_ID, expected_new_last_object_id, expected_num_sent)

    @pytest.mark.parametrize(
        "p_rows_step1, "            # information available in the in memory buffer
        "p_rows_step2, "            # information available in the in memory buffer
        "p_buffer_size, "           # size of the in memory buffer
        "p_send_result, "           # Values returned by the _plugin.plugin_send
        "expected_num_sent_step1, " # expected elements sent
        "expected_num_sent_step2, " # expected elements sent
        "expected_buffer ",         # expected in memory buffer after the _task_send_data operations
        [
            # Case 1
            (
                # p_rows_step1
                [
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {
                                "humidity": 11, "temperature": 38
                            },
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ],
                    [
                        {
                            "id": 2,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {
                                "humidity": 20, "temperature": 201
                            },
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ],
                    [
                        {
                            "id": 4,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {
                                "humidity": 30, "temperature": 301
                            },
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ]
                ],
                # p_rows_step2
                [
                    [
                        {
                            "id": 5,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {
                                "humidity": 50, "temperature": 501
                            },
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ]
                ],

                # p_buffer_size
                3,

                # p_send_result
                [
                    {
                        "data_sent": True,
                        "new_last_object_id": 1,
                        "num_sent": 1,
                     },
                    {
                        "data_sent": True,
                        "new_last_object_id": 2,
                        "num_sent": 1,
                    },
                    {
                        "data_sent": True,
                        "new_last_object_id": 4,
                        "num_sent": 1,
                    },
                    {
                        "data_sent": True,
                        "new_last_object_id": 5,
                        "num_sent": 1,
                    },

                ],

                # expected_num_sent_step1
                3,

                # expected_num_sent_step1
                1,

                #  expected_buffer - 2 dimensions list
                [
                    None,
                    None,
                    None
                ]

            ),
        ]
    )
    @pytest.mark.asyncio
    async def test_task_send_data_cycle_buffer(
                                            self,
                                            event_loop,
                                            p_rows_step1,
                                            p_rows_step2,
                                            p_buffer_size,
                                            p_send_result,
                                            expected_num_sent_step1,
                                            expected_num_sent_step2,
                                            expected_buffer):
        """ Unit tests - _task_send_data - send data filling the buffer and adding new elements """

        async def mock_send_rows(x):
            """ mock the results of the sending operation """
            return p_send_result[x]["data_sent"], p_send_result[x]["new_last_object_id"], p_send_result[x]["num_sent"]

        # GIVEN
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._logger = MagicMock(spec=logging)
        SendingProcess._logger = MagicMock(spec=logging)
        sp._audit = MagicMock(spec=AuditLogger)

        # Configures properly the SendingProcess, enabling JQFilter
        sp._config = {
            'memory_buffer_size': p_buffer_size
        }

        sp._config_from_manager = {
            'applyFilter': {'value': "FALSE"}
        }

        sp._task_send_data_run = True

        sp._task_fetch_data_sem = asyncio.Semaphore(0)
        sp._task_send_data_sem = asyncio.Semaphore(0)

        # Allocates the in memory buffer
        sp._memory_buffer = [None for x in range(p_buffer_size)]

        # Fills the buffer - step 1
        for x in range(len(p_rows_step1)):
            sp._memory_buffer[x] = p_rows_step1[x]

        # WHEN - Starts the fetch 'task'
        # 2 calls of _update_position_reached will be executed
        with patch.object(sp,
                          '_update_position_reached',
                          side_effect=[asyncio.ensure_future(mock_async_call()) for x in range(2)]
                          ) as patched_update_position_reached:

            with patch.object(
                    sp._plugin,
                    'plugin_send',
                    side_effect=[asyncio.ensure_future(mock_send_rows(x)) for x in range(0, len(p_send_result))]):

                task_id = asyncio.ensure_future(sp._task_send_data(STREAM_ID))

                # Lets the _task_fetch_data to run for a while
                await asyncio.sleep(3)

                # THEN - Step 1
                expected_new_last_object_id = p_rows_step1[len(p_rows_step1) - 1][0]["id"]

                assert sp._memory_buffer == expected_buffer
                patched_update_position_reached.assert_called_with(STREAM_ID,
                                                                   expected_new_last_object_id,
                                                                   expected_num_sent_step1)

                # Fills the buffer - step 1
                for x in range(len(p_rows_step2)):
                    sp._memory_buffer[x] = p_rows_step2[x]

                # let handle step 2
                sp._task_fetch_data_sem.release()
                await asyncio.sleep(3)

                # Tear down
                sp._task_send_data_run = False
                sp._task_fetch_data_sem.release()

                await task_id

        # THEN - Step 2
        expected_new_last_object_id = p_rows_step2[len(p_rows_step2) - 1][0]["id"]

        assert sp._memory_buffer == expected_buffer
        patched_update_position_reached.assert_called_with(STREAM_ID, expected_new_last_object_id, expected_num_sent_step2)

    @pytest.mark.parametrize(
        "p_rows, "                  # GIVEN, information available in the in memory buffer
        "p_buffer_size, "           # size of the in memory buffer
        "p_send_result, "           # Values returned by the _plugin.plugin_send
        "expected_num_sent, "       # THEN, expected elements sent
        "expected_buffer ",         # expected in memory buffer after the _task_send_data operations
        [
            (
                # p_rows
                [
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {
                                "humidity": 11, "temperature": 38
                            },
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ],
                    [
                        {
                            "id": 2,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {
                                "humidity": 20, "temperature": 201
                            },
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ],
                    [
                        {
                            "id": 4,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {
                                "humidity": 30, "temperature": 301
                            },
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ]
                ],
                # p_buffer_size
                3,

                # p_send_result - only to elements to force an error calling the plugin_send function
                [
                    {
                        "data_sent": True,
                        "new_last_object_id": 1,
                        "num_sent": 1,
                     },
                    {
                        "data_sent": True,
                        "new_last_object_id": 2,
                        "num_sent": 1,
                    }

                ],

                # expected_num_sent
                3,

                #  expected_buffer - The third element was not sent for the occuring of the error
                [
                    None,
                    None,
                    [
                        {
                            "id": 4,
                            "asset_code": "test_asset_code",
                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                            "reading": {
                                "humidity": 30, "temperature": 301
                            },
                            "user_ts": "16/04/2018 16:32:55"
                        }
                    ]
                ]

            ),
        ]
    )
    # FIXME:
    @pytest.mark.this
    @pytest.mark.asyncio
    async def test_task_send_data_error(
                                            self,
                                            event_loop,
                                            p_rows,
                                            p_buffer_size,
                                            p_send_result,
                                            expected_num_sent,
                                            expected_buffer,
                                            fixture_sp):
        """ Unit tests - _task_send_data - simulates an error while sending,
            to force the error the list p_send_result is filled with less elements respect the required ones,
            so 2 calls will be successful the third one will fail """

        async def mock_send_rows(x):
            """ mock the results of the sending operation """
            return p_send_result[x]["data_sent"], p_send_result[x]["new_last_object_id"], p_send_result[x]["num_sent"]

        # Configures properly the SendingProcess, enabling JQFilter
        fixture_sp._config = {
            'memory_buffer_size': p_buffer_size
        }

        # Allocates the in memory buffer
        fixture_sp._memory_buffer = [None for x in range(p_buffer_size)]

        # Fills the buffer
        for x in range(len(p_rows)):
            fixture_sp._memory_buffer[x] = p_rows[x]

        # WHEN - Starts the fetch 'task'
        with patch.object(fixture_sp, '_update_position_reached', return_value=mock_async_call()):

            with patch.object(SendingProcess._logger, 'error') as patched_logger:
                with patch.object(fixture_sp._audit, 'failure', return_value=mock_audit_failure()) as patched_audit:

                    with patch.object(
                            fixture_sp._plugin,
                            'plugin_send',
                            side_effect=[
                                asyncio.ensure_future(mock_send_rows(x)) for x in range(0, len(p_send_result))]):

                        with pytest.raises(RuntimeError):
                            task_id = asyncio.ensure_future(fixture_sp._task_send_data(STREAM_ID))

                            # Lets the _task_fetch_data to run for a while
                            await asyncio.sleep(3)

                            # Tear down
                            fixture_sp._task_send_data_run = False
                            fixture_sp._task_fetch_data_sem.release()

                            await task_id

        # THEN - Checks log and audit are called in case of en error and the in memory buffer is as expected
        assert patched_logger.called
        assert patched_audit.called
        patched_audit.assert_called_with(SendingProcess._AUDIT_CODE, ANY)

        assert fixture_sp._memory_buffer == expected_buffer

    @pytest.mark.asyncio
    async def test_update_position_reached(self, event_loop):
        """ Unit tests - _update_position_reached """

        async def mock_task():
            """ Dummy async task """
            return True

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._audit = MagicMock(spec=AuditLogger)

        with patch.object(sp, '_last_object_id_update', return_value=mock_task()) as mock_last_object_id_update:
            with patch.object(sp, '_update_statistics', return_value=mock_task()) as mock__update_statistics:
                with patch.object(sp._audit, 'information', return_value=mock_task()) as mock_audit_information:
                    await sp._update_position_reached(STREAM_ID, 1000, 100)

        mock_last_object_id_update.assert_called_with(1000, STREAM_ID)
        mock__update_statistics.assert_called_with(100, STREAM_ID)
        mock_audit_information.assert_called_with(SendingProcess._AUDIT_CODE, {"sentRows": 100})

    @pytest.mark.parametrize("plugin_file, plugin_type, plugin_name", [
        ("empty",      "north", "Empty North Plugin"),
        ("omf",        "north", "OMF North"),
        ("ocs",        "north", "OCS North"),
        ("http_north", "north", "http_north")
    ])
    async def test_standard_plugins(self, plugin_file, plugin_type, plugin_name, event_loop):
        """Tests if the standard plugins are available and loadable and if they have the required methods """

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        # Try to Loads the plugin
        sp._config['north'] = plugin_file
        sp._plugin_load()

        # Evaluates if the plugin has all the required methods
        assert callable(getattr(sp._plugin, 'plugin_info'))
        assert callable(getattr(sp._plugin, 'plugin_init'))
        assert callable(getattr(sp._plugin, 'plugin_send'))
        assert callable(getattr(sp._plugin, 'plugin_shutdown'))
        assert callable(getattr(sp._plugin, 'plugin_reconfigure'))

        # Retrieves the info from the plugin
        plugin_info = sp._plugin.plugin_info()
        assert plugin_info['type'] == plugin_type
        assert plugin_info['name'] == plugin_name

    @pytest.mark.parametrize(
        "p_config,"
        "expected_config",
        [
            # Case 1
            (
                # p_config
                {
                    "enable": {"value": "true"},
                    "duration": {"value": "10"},
                    "source": {"value": SendingProcess._DATA_SOURCE_READINGS},
                    "blockSize": {"value": "10"},
                    "memory_buffer_size": {"value": "10"},
                    "sleepInterval": {"value": "10"},
                    "plugin": {"value": "omf"},

                },
                # expected_config
                {
                    "enable": True,
                    "duration": 10,
                    "source": SendingProcess._DATA_SOURCE_READINGS,
                    "blockSize": 10,
                    "memory_buffer_size": 10,
                    "sleepInterval": 10,
                    "north": "omf",

                },
            ),
        ]
    )
    async def test_retrieve_configuration_good(self,
                                         event_loop,
                                         p_config,
                                         expected_config):
        """ Unit tests - _retrieve_configuration - tests the transformations """

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        with patch.object(sp, '_fetch_configuration', return_value=p_config):
            sp._retrieve_configuration(STREAM_ID)

        assert sp._config['enable'] == expected_config['enable']
        assert sp._config['duration'] == expected_config['duration']
        assert sp._config['source'] == expected_config['source']
        assert sp._config['blockSize'] == expected_config['blockSize']
        assert sp._config['memory_buffer_size'] == expected_config['memory_buffer_size']
        assert sp._config['sleepInterval'] == expected_config['sleepInterval']
        assert sp._config['north'] == expected_config['north']

    async def test_start_stream_not_valid(self, event_loop):
        """ Unit tests - _start - stream_id is not valid """

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        with patch.object(sp, '_is_stream_id_valid', return_value=mock_coro(False)):
            with patch.object(sp, '_plugin_load') as mocked_plugin_load:
                result = await sp._start(STREAM_ID)

        assert not result
        assert not mocked_plugin_load.called

    async def test_start_sp_disabled(self, event_loop):
        """ Unit tests - _start - sending process is disabled """

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._plugin = MagicMock()
        sp._config['enable'] = False
        sp._config_from_manager = {}

        with patch.object(sp, '_is_stream_id_valid', return_value=mock_coro(True)):
            with patch.object(sp, '_retrieve_configuration'):
                with patch.object(sp, '_plugin_load') as mocked_plugin_load:
                    result = await sp._start(STREAM_ID)

        assert not result
        assert not mocked_plugin_load.called

    async def test_start_not_north(self, event_loop):
        """ Unit tests - _start - it is not a north plugin """

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._plugin = MagicMock()
        sp._config['enable'] = True
        sp._config_from_manager = {}

        with patch.object(sp, '_is_stream_id_valid', return_value=mock_coro(True)):
            with patch.object(sp, '_retrieve_configuration'):
                with patch.object(sp, '_plugin_load') as mocked_plugin_load:
                    with patch.object(sp._plugin, 'plugin_info') as mocked_plugin_info:
                        with patch.object(sp, '_is_north_valid', return_value=False) as mocked_is_north_valid:
                            result = await sp._start(STREAM_ID)

        assert not result
        assert mocked_plugin_load.called
        assert mocked_plugin_info.called
        assert mocked_is_north_valid.called

    async def test_start_good(self, event_loop):
        """ Unit tests - _start """

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._plugin = MagicMock()
        sp._config['enable'] = True
        sp._config_from_manager = {}

        with patch.object(sp, '_is_stream_id_valid', return_value=mock_coro(True)) as mocked_is_stream_id_valid:
            with patch.object(sp, '_retrieve_configuration') as mocked_retrieve_configuration:
                with patch.object(sp, '_plugin_load') as mocked_plugin_load:
                    with patch.object(sp._plugin, 'plugin_info') as mocked_plugin_info:
                        with patch.object(sp, '_is_north_valid', return_value=True) as mocked_is_north_valid:
                            with patch.object(sp._plugin, 'plugin_init') as mocked_plugin_init:
                                result = await sp._start(STREAM_ID)

        assert result
        mocked_is_stream_id_valid.called_with(STREAM_ID)
        mocked_retrieve_configuration.called_with(STREAM_ID, True)
        assert mocked_plugin_load.called
        assert mocked_plugin_info.called
        assert mocked_is_north_valid.called
        assert mocked_retrieve_configuration.called
        assert mocked_plugin_init.called
