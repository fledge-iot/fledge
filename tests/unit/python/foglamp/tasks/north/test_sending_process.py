# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import pytest
from unittest.mock import patch, call, MagicMock
from foglamp.common.storage_client.storage_client import ReadingsStorageClient, StorageClient

from foglamp.tasks.north.sending_process import SendingProcess
import foglamp.tasks.north.sending_process as sp_module

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestSendingProcess:
    """Unit tests for the sending_process.py"""

    @pytest.mark.parametrize("plugin_file, plugin_type, plugin_name", [
        ("empty",      "north", "Empty North Plugin"),
        ("omf",        "north", "OMF North"),
        ("ocs",        "north", "OCS North"),
        ("http_north", "north", "http_north")
    ])
    def test_plugins(self, plugin_file, plugin_type, plugin_name):
        """Tests if the defined plugins are available and loadable and if they have the required methods """

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

    @pytest.mark.parametrize("plugin_file, plugin_type, plugin_name, expected_result", [
        ("omf", "north", "OMF North", True),
        ("omf", "north", "Empty North Plugin", False),
        ("omf", "south", "OMF North", False)
    ])
    def test_is_north_valid(self,  plugin_file, plugin_type, plugin_name, expected_result):
        """Tests the possible cases of the function is_north_valid """

        sp = SendingProcess()

        sp._config['north'] = plugin_file
        sp._plugin_load()

        sp._plugin_info = sp._plugin.plugin_info()
        sp._plugin_info['type'] = plugin_type
        sp._plugin_info['name'] = plugin_name

        assert sp._is_north_valid() == expected_result

    def test_last_object_id_read(self):
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

        sp = SendingProcess()
        sp._storage = MagicMock(spec=StorageClient)

        # Good Case
        with patch.object(sp._storage, 'query_tbl', return_value=mock_query_tbl_row_1()) as sp_mocked:
            position = sp._last_object_id_read(1)
            sp_mocked.assert_called_once_with('streams', 'id=1')
            assert position == 10

        # Bad cases
        sp._logger.error = MagicMock()
        with patch.object(sp._storage, 'query_tbl', return_value=mock_query_tbl_row_0()) as sp_mocked:
            try:
                sp._last_object_id_read(1)
            except Exception:
                pass

            sp._logger.error.assert_called_once_with(sp_module._MESSAGES_LIST["e000019"])

        sp._logger.error = MagicMock()
        with patch.object(sp._storage, 'query_tbl', return_value=mock_query_tbl_row_2()) as sp_mocked:
            try:
                sp._last_object_id_read(1)
            except Exception:
                pass

            sp._logger.error.assert_called_once_with(sp_module._MESSAGES_LIST["e000019"])

    def test_load_data_into_memory(self):
        """Test _load_data_into_memory handling and transformations"""

        def mock_fetch_readings():
            """Mocks the fetch function of the ReadingsStorageClient object"""

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

        def mock_query_tbl_with_payload_statistics():
            """Mocks the fetch function of the StorageClient object"""

            rows = {"rows": [
                            {
                                "id": 1,
                                "key": "test_asset_code",
                                "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                                "value": 20,
                                "ts": "16/04/2018 16:32"
                            },
                    ]}
            return rows

        # Checks the Readings handling
        sp = SendingProcess()
        sp._config['source'] = sp._DATA_SOURCE_READINGS

        sp._readings = MagicMock(spec=ReadingsStorageClient)

        # Checks the transformations and especially the adding of the UTC timezone
        with patch.object(sp._readings, 'fetch', return_value=mock_fetch_readings()) as sp_mocked:
            data_transformed = sp._load_data_into_memory(5)

            assert len(data_transformed) == 1
            assert data_transformed[0]['id'] == 1
            assert data_transformed[0]['asset_code'] == "test_asset_code"
            assert data_transformed[0]['reading'] == {"humidity": 11, "temperature": 38}
            assert data_transformed[0]['user_ts'] == "16/04/2018 16:32+00"

        # Checks the Statistics handling
        sp = SendingProcess()
        sp._config['source'] = sp._DATA_SOURCE_STATISTICS

        sp._storage = MagicMock(spec=StorageClient)

        # Checks the transformations for the Statistics especially for the 'reading' field and the fields naming/mapping
        with patch.object(sp._storage, 'query_tbl_with_payload', return_value=mock_query_tbl_with_payload_statistics()) as sp_mocked:
            del data_transformed
            data_transformed = sp._load_data_into_memory(5)

            assert len(data_transformed) == 1
            assert data_transformed[0]['id'] == 1
            assert data_transformed[0]['asset_code'] == "test_asset_code"
            assert data_transformed[0]['reading'] == {"value": 20}
            assert data_transformed[0]['user_ts'] == "16/04/2018 16:32+00"


    # FIXME: todo
    @pytest.mark.skip
    def test_send_data_block(self):
        pass
