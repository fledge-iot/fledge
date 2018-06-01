# -*- coding: utf-8 -*-
""" Unit tests for the North Sending Process """

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import asyncio
import pytest
import logging
import sys
import time
import signal

from unittest.mock import patch, MagicMock

from foglamp.common.storage_client.storage_client import ReadingsStorageClient, StorageClient
from foglamp.tasks.north.sending_process import SendingProcess
import foglamp.tasks.north.sending_process as sp_module
from foglamp.common.audit_logger import AuditLogger

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


STREAM_ID = 1

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
def test_apply_date_format(p_data, expected_data):

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
def test_handling_input_parameters(
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
    def test_is_stream_id_valid(self,
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
        sp._storage = MagicMock(spec=StorageClient)

        if expected_execution == "good":

            with patch.object(sp._storage, 'query_tbl', return_value=p_rows):
                generate_stream_id = sp._is_stream_id_valid(p_stream_id)

            # noinspection PyProtectedMember
            assert not SendingProcess._logger.error.called

            assert generate_stream_id == expected_stream_id_valid

        elif expected_execution == "exception":

            with pytest.raises(ValueError):
                sp._is_stream_id_valid(p_stream_id)

            # noinspection PyProtectedMember
            assert SendingProcess._logger.error.called

    @pytest.mark.parametrize("plugin_file, plugin_type, plugin_name, expected_result", [
        ("omf", "north", "OMF North", True),
        ("omf", "north", "Empty North Plugin", False),
        ("omf", "south", "OMF North", False)
    ])
    def test_is_north_valid(self,  plugin_file, plugin_type, plugin_name, expected_result, event_loop):
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
    @pytest.mark.this
    async def test_load_data_into_memory(self,
                                         loop):
        """ Unit test for - test_load_data_into_memory"""

        async def mock_coro():
            return True

        # Checks the Readings handling
        with patch.object(asyncio, 'get_event_loop', return_value=loop):
            sp = SendingProcess()

        # Tests - READINGS
        sp._config['source'] = sp._DATA_SOURCE_READINGS

        with patch.object(sp, '_load_data_into_memory_readings', return_value=mock_coro()) \
                as mocked_load_data_into_memory_readings:

            await sp._load_data_into_memory(5)
            assert mocked_load_data_into_memory_readings.called

        # Tests - STATISTICS
        sp._config['source'] = sp._DATA_SOURCE_STATISTICS

        with patch.object(sp, '_load_data_into_memory_statistics', return_value=True) \
                as mocked_load_data_into_memory_statistics:

            await  sp._load_data_into_memory(5)
            assert mocked_load_data_into_memory_statistics.called

        # Tests - AUDIT
        sp._config['source'] = sp._DATA_SOURCE_AUDIT

        with patch.object(sp, '_load_data_into_memory_audit', return_value=True) \
                as mocked_load_data_into_memory_audit:

            await  sp._load_data_into_memory(5)
            assert mocked_load_data_into_memory_audit.called


    @pytest.mark.parametrize("p_last_object, p_new_last_object_id, p_num_sent", [
        (10, 20, 10)
    ])
    def test_send_data_block_good(self, p_last_object,  p_new_last_object_id, p_num_sent, event_loop):
        """Tests the _send_data_block, evaluating also the the last object is properly updated"""

        def mock_load_data_into_memory():
            """Mocks _load_data_into_memory"""

            rows = {"rows": [
                            {
                                "id": 1,
                                "asset_code": "test_asset_code",
                                "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                                "reading": {"humidity": 11, "temperature": 38},
                                "user_ts": "16/04/2018 16:32"
                            },
                    ]}
            return rows

        def mock_plugin_send_ok():
            """Mocks _plugin_send - simulating data sent"""

            _data_sent = True
            _new_last_object_id = p_new_last_object_id
            _num_sent = p_num_sent

            return _data_sent, _new_last_object_id, _num_sent

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        # Configures properly the SendingProcess
        sp._config_from_manager = {"applyFilter": {"value": "False"}}
        sp._plugin = MagicMock()
        mock_storage_client = MagicMock(spec=StorageClient)
        sp._audit = AuditLogger(mock_storage_client)

        # Good Case
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            with patch.object(sp, '_last_object_id_read', return_value=p_last_object):
                with patch.object(sp, '_load_data_into_memory', return_value=mock_load_data_into_memory()):

                    with patch.object(sp._plugin, 'plugin_send', return_value=mock_plugin_send_ok()):

                        with patch.object(sp, '_last_object_id_update') \
                                as mocked_last_object_id_update:
                            with patch.object(sp, '_update_statistics') \
                                    as mocked_update_statistics:
                                sp._send_data_block(STREAM_ID)

                                mocked_last_object_id_update.assert_called_once_with(p_new_last_object_id, STREAM_ID)
                                mocked_update_statistics.assert_called_once_with(p_num_sent, STREAM_ID)

    @pytest.mark.parametrize("p_last_object, p_new_last_object_id, p_num_sent", [
        (10, 20, 10)
    ])
    def test_send_data_block_bad(self, p_last_object,  p_new_last_object_id, p_num_sent, event_loop):
        """ Unite tests - _send_data_block - error being raised """

        def mock_load_data_into_memory():
            """Mocks _load_data_into_memory"""

            rows = {"rows": [
                            {
                                "id": 1,
                                "asset_code": "test_asset_code",
                                "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                                "reading": {"humidity": 11, "temperature": 38},
                                "user_ts": "16/04/2018 16:32"
                            },
                    ]}
            return rows

        def mock_plugin_send_bad():
            """Mocks _plugin_send - simulating no data were sent"""

            _data_sent = False
            _new_last_object_id = p_new_last_object_id
            _num_sent = p_num_sent

            return _data_sent, _new_last_object_id, _num_sent

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        # Configures properly the SendingProcess
        sp._config_from_manager = {"applyFilter": {"value": "False"}}
        sp._plugin = MagicMock()
        mock_storage_client = MagicMock(spec=StorageClient)
        sp._audit = AuditLogger(mock_storage_client)

        # Bad Case
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            with patch.object(sp, '_last_object_id_read', return_value=p_last_object):
                with patch.object(sp, '_load_data_into_memory', return_value=mock_load_data_into_memory()):

                    with patch.object(sp._plugin, 'plugin_send', return_value=mock_plugin_send_bad()):

                        with patch.object(sp, '_last_object_id_update') as mocked_last_object_id_update:
                            with patch.object(sp, '_update_statistics') as mocked_update_statistics:
                                sp._send_data_block(STREAM_ID)

                                assert not mocked_last_object_id_update.called
                                assert not mocked_update_statistics.called

    @pytest.mark.parametrize(
        "p_jqfilter, "
        "p_data, "
        "expected_data ",
        [
            # Case - add the field 'addedField': 512
            (
                # p_jqfilter
                "(.[]|.reading|.addedField)=512",

                # p_data
                [
                    {
                        "id": 1,
                        "asset_code": "test_asset_code",
                        "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                        "reading": {
                            "humidity": 11, "temperature": 38
                        },
                        "user_ts": "16/04/2018 16:32"
                    },
                ],

                # expected_data
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
                        'user_ts': '16/04/2018 16:32'
                    }
                ],
            ),
        ]
    )
    def test_send_data_block_jqfilter(self,
                                      event_loop,
                                      p_jqfilter,
                                      p_data,
                                      expected_data):
        """ Tests JQFilter functionalities of _send_data_block"""

        def mock_plugin_send_ok():
            """Mocks _plugin_send - simulating data sent"""

            return True, 2, 1

        SendingProcess._logger = MagicMock(spec=logging)

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        # Configures properly the SendingProcess, enabling JQFilter
        sp._logger = MagicMock(spec=logging)
        sp._storage = MagicMock(spec=StorageClient)
        sp._plugin = MagicMock()

        mock_storage_client = MagicMock(spec=StorageClient)
        sp._audit = AuditLogger(mock_storage_client)

        sp._config_from_manager = {
            "applyFilter": {"value": "TRUE"},
            "filterRule": {"value": p_jqfilter}
        }
        sp._plugin_handle = []

        # Executes the call
        with patch.object(sp, '_last_object_id_read', return_value=1):
            with patch.object(sp, '_load_data_into_memory', return_value=p_data):

                with patch.object(sp._plugin, 'plugin_send', return_value=mock_plugin_send_ok()) as mocked_plugin_send:
                    with patch.object(sp, '_last_object_id_update'):
                        with patch.object(sp, '_update_statistics'):
                            with patch.object(asyncio, 'get_event_loop', return_value=event_loop):

                                sp._send_data_block(STREAM_ID)

                mocked_plugin_send.assert_called_once_with([], expected_data, STREAM_ID)

    @pytest.mark.parametrize("plugin_file, plugin_type, plugin_name", [
        ("empty",      "north", "Empty North Plugin"),
        ("omf",        "north", "OMF North"),
        ("ocs",        "north", "OCS North"),
        ("http_north", "north", "http_north")
    ])
    def test_standard_plugins(self, plugin_file, plugin_type, plugin_name, event_loop):
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


    def test_last_object_id_read(self, event_loop):
        """Tests the possible cases for the function last_object_id_read """

        def mock_query_tbl_row_1():
            """Mocks the query_tbl function of the StorageClient object - good case"""

            rows = {"rows": [{"last_object": 10}]}
            return rows

        def mock_query_tbl_row_0():
            """Mocks the query_tbl function of the StorageClient object - base case"""

            rows = {"rows": []}
            return rows

        def mock_query_tbl_row_2():
            """Mocks the query_tbl function of the StorageClient object - base case"""

            rows = {"rows": [{"last_object": 10}, {"last_object": 11}]}
            return rows

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._storage = MagicMock(spec=StorageClient)

        # Good Case
        with patch.object(sp._storage, 'query_tbl', return_value=mock_query_tbl_row_1()) as sp_mocked:
            position = sp._last_object_id_read(1)
            sp_mocked.assert_called_once_with('streams', 'id=1')
            assert position == 10

        # Bad cases
        sp._logger.error = MagicMock()
        with patch.object(sp._storage, 'query_tbl', return_value=mock_query_tbl_row_0()):
            # noinspection PyBroadException
            try:
                sp._last_object_id_read(1)
            except Exception:
                pass

            sp._logger.error.assert_called_once_with(sp_module._MESSAGES_LIST["e000019"])

        sp._logger.error = MagicMock()
        with patch.object(sp._storage, 'query_tbl', return_value=mock_query_tbl_row_2()):
            # noinspection PyBroadException
            try:
                sp._last_object_id_read(1)
            except Exception:
                pass

            sp._logger.error.assert_called_once_with(sp_module._MESSAGES_LIST["e000019"])


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
                            "user_ts": "16/04/2018 16:32"
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
                        "user_ts": "16/04/2018 16:32+00"
                    },
                ]

            )
        ]
    )
    def test_load_data_into_memory_readings(self,
                                            event_loop,
                                            p_rows,
                                            expected_rows):
        """Test _load_data_into_memory handling and transformations for the readings """

        # Checks the Readings handling
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._config['source'] = sp._DATA_SOURCE_READINGS

        sp._readings = MagicMock(spec=ReadingsStorageClient)

        # Checks the transformations and especially the adding of the UTC timezone
        with patch.object(sp._readings, 'fetch', return_value=p_rows):

            generated_rows = sp._load_data_into_memory(5)

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
                        "user_ts": "16/04/2018 16:32"
                    },
                ],
                # expected_rows,
                [
                    {
                        "id": 1,
                        "asset_code": "test_asset_code",
                        "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                        "reading": {"humidity": 11, "temperature": 38},
                        "user_ts": "16/04/2018 16:32+00"
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
                            "user_ts": "16/04/2018 16:32"
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
                            "user_ts": "16/04/2018 16:32+00"
                        },
                    ]

            )
        ]
    )
    def test_transform_in_memory_data_readings(self,
                                               event_loop,
                                               p_rows,
                                               expected_rows):
        """ Unit test for - _transform_in_memory_data_readings"""

        # Checks the Readings handling
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._config['source'] = sp._DATA_SOURCE_READINGS

        sp._readings = MagicMock(spec=ReadingsStorageClient)

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
                            "ts": "16/04/2018 16:32"
                        },
                    ]
                },
                # expected_rows,
                [
                    {
                        "id": 1,
                        "asset_code": "test_asset_code",
                        "reading": {"value": 20},
                        "user_ts": "16/04/2018 16:32+00"
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
                                "ts": "16/04/2018 16:32"
                            },
                        ]
                    },
                    # expected_rows,
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "reading": {"value": 21},
                            "user_ts": "16/04/2018 16:32+00"
                        },
                    ]

            )

        ]
    )
    def test_load_data_into_memory_statistics(self,
                                              event_loop,
                                              p_rows,
                                              expected_rows):
        """Test _load_data_into_memory handling and transformations for the statistics """

        # Checks the Statistics handling
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._config['source'] = sp._DATA_SOURCE_STATISTICS

        sp._storage = MagicMock(spec=StorageClient)

        # Checks the transformations for the Statistics especially for the 'reading' field and the fields naming/mapping
        with patch.object(sp._storage, 'query_tbl_with_payload', return_value=p_rows):

            generated_rows = sp._load_data_into_memory(5)

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
                            "ts": "16/04/2018 16:32"
                        },
                ],
                # expected_rows,
                [
                    {
                        "id": 1,
                        "asset_code": "test_asset_code",
                        "reading": {"value": 20},
                        "user_ts": "16/04/2018 16:32+00"
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
                            "ts": "16/04/2018 16:32"
                        },
                    ],
                    # expected_rows,
                    [
                        {
                            "id": 1,
                            "asset_code": "test_asset_code",
                            "reading": {"value": 21},
                            "user_ts": "16/04/2018 16:32+00"
                        },
                    ]

            )

        ]
    )
    def test_transform_in_memory_data_statistics(self,
                                                 event_loop,
                                                 p_rows,
                                                 expected_rows):
        """ Unit test for - _transform_in_memory_data_statistics"""

        # Checks the Statistics handling
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._config['source'] = sp._DATA_SOURCE_STATISTICS

        sp._storage = MagicMock(spec=StorageClient)

        # Checks the transformations for the Statistics especially for the 'reading' field and the fields naming/mapping
        generated_rows = sp._transform_in_memory_data_statistics(p_rows)

        assert len(generated_rows) == 1
        assert generated_rows == expected_rows

    def test_load_data_into_memory_audit(self,
                                         event_loop
                                         ):
        """ Unit test for - _load_data_into_memory_audit, NB the function is currently not implemented """

        # Checks the Statistics handling
        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._config['source'] = sp._DATA_SOURCE_AUDIT
        sp._storage = MagicMock(spec=StorageClient)

        generated_rows = sp._load_data_into_memory_audit(5)

        assert len(generated_rows) == 0
        assert generated_rows == ""

    @pytest.mark.parametrize(
        "p_duration, "
        "p_sleep_interval, "
        "p_data_sent, "
        "expected_calls, "
        "expected_time ",
        [
            # Cases

            # p_duration - p_sleep_interval  - p_data_sent - expected_calls - expected_time
            (3,            1,                  False,        3,               3),
            (3,            1,                  True,         3,               3),

        ]
    )
    def test_send_data_good(self,
                            event_loop,
                            p_duration,
                            p_sleep_interval,
                            p_data_sent,
                            expected_calls,
                            expected_time):
        """ Unit tests - send_data """

        SendingProcess._logger = MagicMock(spec=logging)

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        # Configures properly the SendingProcess, enabling JQFilter
        sp._config = {
            'duration': p_duration,
            'sleepInterval': p_sleep_interval
        }

        # Executes the call
        start_time = time.time()

        with patch.object(sp, '_send_data_block', return_value=p_data_sent) as mocked_send_data_block:

            sp.send_data(STREAM_ID)

        if not p_data_sent:
            assert mocked_send_data_block.call_count == expected_calls

            # It considers a reasonable tolerance
            elapsed_seconds = time.time() - start_time
            assert expected_time <= elapsed_seconds <= (expected_time + 10)

        elif p_data_sent:
            # Not sleep is executed in case of data were sent and so a lot of calls are expected
            assert mocked_send_data_block.call_count >= expected_calls

    def test_send_data_stop_exec(self, event_loop):
        """ Unit tests - send_data - simulates the termination signal """

        SendingProcess._logger = MagicMock(spec=logging)
        SendingProcess._stop_execution = True

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        # Configures properly the SendingProcess, enabling JQFilter
        sp._config = {
            'duration': 10,
            'sleepInterval': 1
        }

        with patch.object(sp, '_send_data_block', return_value=True) as mocked_send_data_block:

            sp.send_data(STREAM_ID)

        assert not mocked_send_data_block.called

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
                    "sleepInterval": {"value": "10"},
                    "plugin": {"value": "omf"},

                },
                # expected_config
                {
                    "enable": True,
                    "duration": 10,
                    "source": SendingProcess._DATA_SOURCE_READINGS,
                    "blockSize": 10,
                    "sleepInterval": 10,
                    "north": "omf",

                },
            ),
        ]
    )
    def test_retrieve_configuration_good(self,
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
        assert sp._config['sleepInterval'] == expected_config['sleepInterval']
        # Note
        assert sp._config['north'] == expected_config['north']

    def test__start_stream_not_valid(self, event_loop):
        """ Unit tests - _start - stream_id is not valid """

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        with patch.object(sp, '_is_stream_id_valid', return_value=False):
            with patch.object(sp, '_plugin_load') as mocked_plugin_load:
                result = sp._start(STREAM_ID)

        assert not result
        assert not mocked_plugin_load.called

    def test__start_sp_disabled(self, event_loop):
        """ Unit tests - _start - sending process is disabled """

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._plugin = MagicMock()
        sp._config['enable'] = False
        sp._config_from_manager = {}

        with patch.object(sp, '_is_stream_id_valid', return_value=True):
            with patch.object(sp, '_retrieve_configuration'):
                with patch.object(sp, '_plugin_load') as mocked_plugin_load:
                    result = sp._start(STREAM_ID)

        assert not result
        assert not mocked_plugin_load.called

    def test__start_not_north(self, event_loop):
        """ Unit tests - _start - it is not a north plugin """

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._plugin = MagicMock()
        sp._config['enable'] = True
        sp._config_from_manager = {}

        with patch.object(sp, '_is_stream_id_valid', return_value=True):
            with patch.object(sp, '_retrieve_configuration'):
                with patch.object(sp, '_plugin_load') as mocked_plugin_load:
                    with patch.object(sp._plugin, 'plugin_info') as mocked_plugin_info:
                        with patch.object(sp, '_is_north_valid', return_value=False) as mocked_is_north_valid:

                            result = sp._start(STREAM_ID)

        assert not result
        assert mocked_plugin_load.called
        assert mocked_plugin_info.called
        assert mocked_is_north_valid.called

    def test__start_good(self, event_loop):
        """ Unit tests - _start """

        with patch.object(asyncio, 'get_event_loop', return_value=event_loop):
            sp = SendingProcess()

        sp._plugin = MagicMock()
        sp._config['enable'] = True
        sp._config_from_manager = {}

        with patch.object(sp, '_is_stream_id_valid', return_value=True) as mocked_is_stream_id_valid:
            with patch.object(sp, '_retrieve_configuration') as mocked_retrieve_configuration:
                with patch.object(sp, '_plugin_load') as mocked_plugin_load:
                    with patch.object(sp._plugin, 'plugin_info') as mocked_plugin_info:
                        with patch.object(sp, '_is_north_valid', return_value=True) as mocked_is_north_valid:
                            with patch.object(sp._plugin, 'plugin_init') as mocked_plugin_init:
                                result = sp._start(STREAM_ID)

        assert result
        mocked_is_stream_id_valid.called_with(STREAM_ID)
        mocked_retrieve_configuration.called_with(STREAM_ID, True)
        assert mocked_plugin_load.called
        assert mocked_plugin_info.called
        assert mocked_is_north_valid.called
        assert mocked_retrieve_configuration.called
        assert mocked_plugin_init.called

