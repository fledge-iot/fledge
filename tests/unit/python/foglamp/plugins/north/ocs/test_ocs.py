# -*- coding: utf-8 -*-
""" Unit tests for the OCS plugin """

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import pytest
import json
import logging

from unittest.mock import patch, MagicMock, ANY

from foglamp.plugins.north.ocs import ocs
from foglamp.tasks.north.sending_process import SendingProcess
import foglamp.tasks.north.sending_process as module_sp
from foglamp.common.storage_client.storage_client import StorageClientAsync

_STREAM_ID = 1

async def mock_async_call(p1=ANY):
    """ mocks a generic async function """
    return p1


@pytest.fixture
def fixture_ocs(event_loop):
    """"  Configures the OMF instance for the tests """

    _omf = MagicMock()

    ocs._logger = MagicMock(spec=logging)
    ocs._config_omf_types = {"type-id": {"value": "0001"}}

    return ocs


@pytest.fixture
def fixture_ocs_north(event_loop):
    """"  Configures the OMF instance for the tests """

    sending_process_instance = MagicMock()
    config = []
    config_omf_types = []

    _logger = MagicMock(spec=logging)

    ocs_north = ocs.OCSNorthPlugin(sending_process_instance, config, config_omf_types, _logger)

    ocs_north._sending_process_instance._storage_async = MagicMock(spec=StorageClientAsync)

    return ocs_north


@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "north", "ocs")
class TestOCS:
    """Unit tests related to the public methods of the OCS plugin """

    def test_plugin_info(self):

        plugin_info = ocs.plugin_info()

        assert plugin_info == {
            'name': "OCS North",
            'version': "1.0.0",
            'type': "north",
            'interface': "1.0",
            'config': ocs._CONFIG_DEFAULT_OMF
        }

    def test_plugin_init_good(self):
        """Tests plugin_init using a good set of values"""

        ocs._logger = MagicMock()

        # Used to check the conversions
        data = {
                "stream_id": {"value": 1},

                "_CONFIG_CATEGORY_NAME":  module_sp.SendingProcess._CONFIG_CATEGORY_NAME,
                "URL": {"value": "test_URL"},
                "producerToken": {"value": "test_producerToken"},
                "OMFMaxRetry": {"value": "100"},
                "OMFRetrySleepTime": {"value": "100"},
                "OMFHttpTimeout": {"value": "100"},
                "StaticData": {
                    "value": json.dumps(
                        {
                            "Location": "Palo Alto",
                            "Company": "Dianomic"
                        }
                    )
                },
                "destination_type": {"value": "3"},
                'sending_process_instance': MagicMock(spec=SendingProcess),
                "formatNumber": {"value": "float64"},
                "formatInteger": {"value": "int64"},

        }

        config_default_omf_types = ocs._CONFIG_DEFAULT_OMF_TYPES
        config_default_omf_types["type-id"]["value"] = "0001"
        data["debug_level"] = None
        data["log_performance"] = None
        data["destination_id"] = 1
        data["stream_id"] = 1

        with patch.object(data['sending_process_instance'], '_fetch_configuration',
                          return_value=config_default_omf_types):
            config = ocs.plugin_init(data)

        assert config['_CONFIG_CATEGORY_NAME'] == module_sp.SendingProcess._CONFIG_CATEGORY_NAME
        assert config['URL'] == "test_URL"
        assert config['producerToken'] == "test_producerToken"
        assert config['OMFMaxRetry'] == 100
        assert config['OMFRetrySleepTime'] == 100
        assert config['OMFHttpTimeout'] == 100

        # Check conversion from String to Dict
        assert isinstance(config['StaticData'], dict)

    @pytest.mark.parametrize("data", [

            # Bad case 1 - StaticData is a python dict instead of a string containing a dict
            {
                "stream_id": {"value": 1},

                "_CONFIG_CATEGORY_NAME":  module_sp.SendingProcess._CONFIG_CATEGORY_NAME,
                "URL": {"value": "test_URL"},
                "producerToken": {"value": "test_producerToken"},
                "OMFMaxRetry": {"value": "100"},
                "OMFRetrySleepTime": {"value": "100"},
                "OMFHttpTimeout": {"value": "100"},
                "StaticData": {
                    "value":
                        {
                            "Location": "Palo Alto",
                            "Company": "Dianomic"
                        }
                },

                'sending_process_instance': MagicMock(spec=SendingProcess),

                "formatNumber": {"value": "float64"},
                "formatInteger": {"value": "int64"},
            },

            # Bad case 2 - OMFMaxRetry, bad value expected an int it is a string
            {
                "stream_id": {"value": 1},

                "_CONFIG_CATEGORY_NAME": module_sp.SendingProcess._CONFIG_CATEGORY_NAME,
                "URL": {"value": "test_URL"},
                "producerToken": {"value": "test_producerToken"},
                "OMFMaxRetry": {"value": "xxx"},
                "OMFRetrySleepTime": {"value": "100"},
                "OMFHttpTimeout": {"value": "100"},
                "StaticData": {
                    "value": json.dumps(
                        {
                            "Location": "Palo Alto",
                            "Company": "Dianomic"
                        }
                    )
                },

                'sending_process_instance': MagicMock(spec=SendingProcess),

                "formatNumber": {"value": "float64"},
                "formatInteger": {"value": "int64"},
            },

            # Bad case 3- formatNumber not defined
            {
                "stream_id": {"value": 1},
    
                "_CONFIG_CATEGORY_NAME": module_sp.SendingProcess._CONFIG_CATEGORY_NAME,
                "URL": {"value": "test_URL"},
                "producerToken": {"value": "test_producerToken"},
                "OMFMaxRetry": {"value": "100"},
                "OMFRetrySleepTime": {"value": "100"},
                "OMFHttpTimeout": {"value": "100"},
                "StaticData": {
                    "value": json.dumps(
                        {
                            "Location": "Palo Alto",
                            "Company": "Dianomic"
                        }
                    )
                },
    
                'sending_process_instance': MagicMock(spec=SendingProcess),
    
                "formatInteger": {"value": "int64"}
            },

        
            # Bad case 4 - formatInteger not defined
            {
                "stream_id": {"value": 1},
    
                "_CONFIG_CATEGORY_NAME": module_sp.SendingProcess._CONFIG_CATEGORY_NAME,
                "URL": {"value": "test_URL"},
                "producerToken": {"value": "test_producerToken"},
                "OMFMaxRetry": {"value": "100"},
                "OMFRetrySleepTime": {"value": "100"},
                "OMFHttpTimeout": {"value": "100"},
                "StaticData": {
                    "value": json.dumps(
                        {
                            "Location": "Palo Alto",
                            "Company": "Dianomic"
                        }
                    )
                },
    
                'sending_process_instance': MagicMock(spec=SendingProcess),
    
                "formatNumber": {"value": "float64"}
            }

    ])
    def test_plugin_init_bad(self, data):
        """Tests plugin_init using an invalid set of values"""

        ocs._logger = MagicMock()

        with pytest.raises(Exception):
            ocs.plugin_init(data)

    @pytest.mark.parametrize(
        "ret_transform_in_memory_data, "
        "p_raw_data, ",
        [
            (
                # ret_transform_in_memory_data
                # is_data_available - new_position - num_sent
                [True,                20,            10],

                # raw_data
                [
                    {
                        "id": 10,
                        "asset_code": "test_asset_code",
                        "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                        "reading": {"humidity": 100, "temperature": 1001},
                        "user_ts": '2018-04-20 09:38:50.163164+00'
                    }
                ]
             )
        ]
    )
    @pytest.mark.asyncio
    async def test_plugin_send_success(self,
                                       ret_transform_in_memory_data,
                                       p_raw_data,
                                       fixture_ocs
                                       ):

        data = MagicMock()

        with patch.object(fixture_ocs.OCSNorthPlugin,
                          'transform_in_memory_data',
                          return_value=ret_transform_in_memory_data) as patched_transform_in_memory_data:
            with patch.object(fixture_ocs.OCSNorthPlugin,
                              'create_omf_objects',
                              return_value=mock_async_call()) as patched_create_omf_objects:
                with patch.object(fixture_ocs.OCSNorthPlugin,
                                  'send_in_memory_data_to_picromf',
                                  return_value=mock_async_call()) as patched_send_in_memory_data_to_picromf:
                    await fixture_ocs.plugin_send(data, p_raw_data, _STREAM_ID)

        assert patched_transform_in_memory_data.called
        assert patched_create_omf_objects.called
        assert patched_send_in_memory_data_to_picromf.called

    @pytest.mark.parametrize(
        "ret_transform_in_memory_data, "
        "p_raw_data, ",
        [
            (
                # ret_transform_in_memory_data
                # is_data_available - new_position - num_sent
                [True,                20,            10],

                # raw_data
                {
                    "id": 10,
                    "asset_code": "test_asset_code",
                    "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                    "reading": {"humidity": 100, "temperature": 1001},
                    "user_ts": '2018-04-20 09:38:50.163164+00'
                }
             )

        ]
    )
    @pytest.mark.asyncio
    async def test_plugin_send_error(
                                    self,
                                    fixture_ocs,
                                    ret_transform_in_memory_data,
                                    p_raw_data
                                     ):
        """ Unit test for - plugin_send - error handling case
           it tests especially if the ocs objects are created again in case of a communication error
           
           NOTE : the stderr is redirected to avoid the print of an error message that could be ignored.
        """

        data = MagicMock()

        with patch.object(fixture_ocs.OCSNorthPlugin,
                          'transform_in_memory_data',
                          return_value=ret_transform_in_memory_data
                          ) as patched_transform_in_memory_data:

            with patch.object(fixture_ocs.OCSNorthPlugin,
                              'create_omf_objects',
                              return_value=mock_async_call()
                              ) as patched_create_omf_objects:

                with patch.object(fixture_ocs.OCSNorthPlugin,
                                  'send_in_memory_data_to_picromf',
                                  side_effect=KeyError('mocked object generated an exception')
                                  ) as patched_send_in_memory_data_to_picromf:

                    with patch.object(fixture_ocs.OCSNorthPlugin,
                                      'deleted_omf_types_already_created',
                                      return_value=mock_async_call()
                                      ) as patched_deleted_omf_types_already_created:

                        with pytest.raises(Exception):
                            await fixture_ocs.plugin_send(data, p_raw_data,
                                                                                              _STREAM_ID)
        assert patched_transform_in_memory_data.called
        assert patched_create_omf_objects.called
        assert patched_send_in_memory_data_to_picromf.called
        assert patched_deleted_omf_types_already_created.called

    def test_plugin_shutdown(self):

        ocs._logger = MagicMock()
        data = []
        ocs.plugin_shutdown([data])

    def test_plugin_reconfigure(self):

        ocs._logger = MagicMock()
        ocs.plugin_reconfigure()


class TestOCSNorthPlugin:
    """Unit tests related to OCSNorthPlugin, methods used internally to the plugin"""

    @pytest.mark.parametrize(
        "p_test_data, "
        "p_type_id, "
        "p_static_data, "
        "expected_typename,"
        "expected_omf_type",
        [
            # Case 1 - pressure / Number
            (
                # Origin - Sensor data
                {"asset_code": "pressure", "asset_data": {"pressure": 921.6}},

                # type_id
                "0001",

                # Static Data
                {
                    "Location": "Palo Alto",
                    "Company": "Dianomic"
                },

                # Expected
                'pressure_typename',
                {
                    'pressure_typename':
                    [
                        {
                            'classification': 'static',
                            'id': '0001_pressure_typename_sensor',
                            'properties': {
                                            'Company': {'type': 'string'},
                                            'Name': {'isindex': True, 'type': 'string'},
                                            'Location': {'type': 'string'}
                            },
                            'type': 'object'
                        },
                        {
                            'classification': 'dynamic',
                            'id': '0001_pressure_typename_measurement',
                            'properties': {


                                'Time': {
                                        'isindex': True,
                                        'format': 'date-time',
                                        'type': 'string'
                                },
                                'pressure': {
                                        'type': 'number',
                                        'format': 'float64'
                                }
                            },
                            'type': 'object'
                         }
                    ]
                }
            ),
            # Case 2 - luxometer / Integer
            (
                    # Origin - Sensor data
                    {"asset_code": "luxometer", "asset_data": {"lux": 20}},

                    # type_id
                    "0002",

                    # Static Data
                    {
                        "Location": "Palo Alto",
                        "Company": "Dianomic"
                    },

                    # Expected
                    'luxometer_typename',
                    {
                        'luxometer_typename':
                            [
                                {
                                    'classification': 'static',
                                    'id': '0002_luxometer_typename_sensor',
                                    'properties': {
                                        'Company': {'type': 'string'},
                                        'Name': {'isindex': True, 'type': 'string'},
                                        'Location': {'type': 'string'}
                                    },
                                    'type': 'object'
                                },
                                {
                                    'classification': 'dynamic',
                                    'id': '0002_luxometer_typename_measurement',
                                    'properties': {
                                        'Time': {'isindex': True, 'format': 'date-time', 'type': 'string'},
                                        'lux': {
                                                'type': 'integer',
                                                'format': 'int64'
                                        }
                                    },
                                    'type': 'object'
                                }
                            ]
                    }

            )

        ]
    )
    @pytest.mark.asyncio
    async def test_create_omf_type_automatic(
                                        self,
                                        p_test_data,
                                        p_type_id,
                                        p_static_data,
                                        expected_typename,
                                        expected_omf_type,
                                        fixture_ocs_north):
        """ Unit test for - _create_omf_type_automatic - successful case
            Tests the generation of the OMF messages starting from Asset name and data
            using Automatic OMF Type Mapping"""

        fixture_ocs_north._config_omf_types = {"type-id": {"value": p_type_id}}

        fixture_ocs_north._config = {}
        fixture_ocs_north._config["StaticData"] = p_static_data
        fixture_ocs_north._config["formatNumber"] = "float64"
        fixture_ocs_north._config["formatInteger"] = "int64"

        with patch.object(fixture_ocs_north,
                          'send_in_memory_data_to_picromf',
                          return_value=mock_async_call()
                          ) as patched_send_in_memory_data_to_picromf:

            typename, omf_type = await fixture_ocs_north._create_omf_type_automatic(p_test_data)

        assert typename == expected_typename
        assert omf_type == expected_omf_type

        assert patched_send_in_memory_data_to_picromf.called
        patched_send_in_memory_data_to_picromf.assert_any_call("Type", expected_omf_type[expected_typename])
