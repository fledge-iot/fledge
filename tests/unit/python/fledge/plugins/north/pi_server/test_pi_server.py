# -*- coding: utf-8 -*-
""" Unit tests for the omf plugin """

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import asyncio
import logging
import pytest
import json
import time
import ast

import aiohttp

from unittest.mock import patch, MagicMock, ANY

from fledge.tasks.north.sending_process import SendingProcess
from fledge.plugins.north.pi_server import pi_server
import fledge.tasks.north.sending_process as module_sp

from fledge.common.storage_client import payload_builder

from fledge.common.storage_client.storage_client import StorageClientAsync

_STREAM_ID = 1


# noinspection PyProtectedMember
@pytest.fixture
def fixture_omf(event_loop):
    """"  Configures the OMF instance for the tests """

    _omf = MagicMock()

    pi_server._logger = MagicMock(spec=logging)
    pi_server._config_omf_types = {"type-id": {"value": "0001"}}

    return pi_server

# noinspection PyProtectedMember
@pytest.fixture
def fixture_omf_north(event_loop):
    """"  Configures the OMF instance for the tests """

    sending_process_instance = MagicMock()
    config = []
    config_omf_types = []

    _logger = MagicMock(spec=logging)

    omf_north = pi_server.PIServerNorthPlugin(sending_process_instance, config, config_omf_types, _logger)

    omf_north._sending_process_instance._storage_async = MagicMock(spec=StorageClientAsync)

    return omf_north


async def mock_async_call(p1=ANY):
    """ mocks a generic async function """
    return p1


class MockAiohttpClientSession(MagicMock):
    """" mock the aiohttp.ClientSession context manager """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.code = args[0]
        self.text = args[1]

    async def __aenter__(self):
        mock_response = MagicMock(spec=aiohttp.ClientResponse)
        mock_response.status = self.code
        mock_response.text.side_effect = [mock_async_call(self.text)]

        return mock_response

    async def __aexit__(self, *args):
        return None


class MockAiohttpClientSessionSuccess(MagicMock):
    """" mock the aiohttp.ClientSession context manager """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def __aenter__(self):
        mock_response = MagicMock(spec=aiohttp.ClientResponse)
        mock_response.status = 200
        mock_response.text.side_effect = [mock_async_call('SUCCESS')]

        return mock_response

    async def __aexit__(self, *args):
        return None


class MockAiohttpClientSessionError(MagicMock):
    """" mock the aiohttp.ClientSession context manager """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def __aenter__(self):
        mock_response = MagicMock(spec=aiohttp.ClientResponse)
        mock_response.status = 400
        mock_response.text.side_effect = [mock_async_call('ERROR')]

        return mock_response

    async def __aexit__(self, *args):
        return None


# noinspection PyUnresolvedReferences
@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "north", "pi_server")
class TestPiServer:
    """Unit tests related to the public methods of the omf plugin """

    def test_plugin_info(self):

        assert pi_server.plugin_info() == {
            'name': "PI Server North",
            'version': "1.0.0",
            'type': "north",
            'interface': "1.0",
            'config': pi_server._CONFIG_DEFAULT_OMF
        }

    def test_plugin_init_good(self):
        """Tests plugin_init using a good set of values"""

        pi_server._logger = MagicMock()

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
                "destination_type": {"value": "1"},
                'sending_process_instance': MagicMock(spec=SendingProcess),
                "formatNumber": {"value": "float64"},
                "formatInteger": {"value": "int64"},
                "notBlockingErrors": {"value": "{'id': 400, 'message': 'none'}"},
                "compression": {"value": "true"}

        }

        config_default_omf_types = pi_server.CONFIG_DEFAULT_OMF_TYPES
        config_default_omf_types["type-id"]["value"] = "0001"
        data["debug_level"] = None
        data["log_performance"] = None
        data["destination_id"] = 1
        data["stream_id"] = 1

        with patch.object(data['sending_process_instance'], '_fetch_configuration',
                          return_value=config_default_omf_types):
            config = pi_server.plugin_init(data)

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

                'sending_process_instance': MagicMock()
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

                'sending_process_instance': MagicMock()
            }

    ])
    def test_plugin_init_bad(self, data):
        """Tests plugin_init using an invalid set of values"""

        pi_server._logger = MagicMock()

        with pytest.raises(Exception):
            pi_server.plugin_init(data)

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
                    "reading": {"humidity": 100, "temperature": 1001},
                    "user_ts": '2018-04-20 09:38:50.163164+00'
                }
             ),
            (
                # ret_transform_in_memory_data
                # is_data_available - new_position - num_sent
                [False, 20, 10],

                # raw_data
                {
                    "id": 10,
                    "asset_code": "test_asset_code",
                    "reading": {"humidity": 100, "temperature": 1001},
                    "user_ts": '2018-04-20 09:38:50.163164+00'
                }
            ),

        ]
    )
    @pytest.mark.asyncio
    async def test_plugin_send_success(
                                        self,
                                        event_loop,
                                        fixture_omf,
                                        ret_transform_in_memory_data,
                                        p_raw_data
                                        ):
        """ Unit test for - plugin_send - successful case """

        data = MagicMock()

        if ret_transform_in_memory_data[0]:
            # data_available

            with patch.object(fixture_omf.PIServerNorthPlugin,
                              'transform_in_memory_data',
                              return_value=ret_transform_in_memory_data):

                with patch.object(fixture_omf.PIServerNorthPlugin,
                                  'create_omf_objects',
                                  return_value=mock_async_call()
                                  ) as patched_create_omf_objects:
                    with patch.object(fixture_omf.PIServerNorthPlugin,
                                      'send_in_memory_data_to_picromf',
                                      return_value=mock_async_call()
                                      ) as patched_send_in_memory_data_to_picromf:
                        data_sent, new_position, num_sent = await fixture_omf.plugin_send(data, p_raw_data, _STREAM_ID)

            assert patched_create_omf_objects.called
            assert patched_send_in_memory_data_to_picromf.called

            assert data_sent
            assert new_position == ret_transform_in_memory_data[1]
            assert num_sent == ret_transform_in_memory_data[2]

        else:
            # no data_available

            with patch.object(fixture_omf.PIServerNorthPlugin,
                              'transform_in_memory_data',
                              return_value=ret_transform_in_memory_data):

                data_sent, new_position, num_sent = await fixture_omf.plugin_send(data, p_raw_data, _STREAM_ID)

            assert not data_sent

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
                    "reading": {"humidity": 100, "temperature": 1001},
                    "user_ts": '2018-04-20 09:38:50.163164+00'
                }
             )

        ]
    )
    @pytest.mark.asyncio
    async def test_plugin_send_error(
                                        self,
                                        event_loop,
                                        fixture_omf,
                                        ret_transform_in_memory_data,
                                        p_raw_data
                                        ):
        """ Unit test for - plugin_send - error handling case
           it tests especially if the omf objects are created again in case of a communication error
           NOTE : the test will print a message to the stderr containing 'mocked object generated an exception'
                  the message is not to be intended an as error as it is part of the successful test.
        """

        data = MagicMock()

        with patch.object(fixture_omf.PIServerNorthPlugin,
                          'transform_in_memory_data',
                          return_value=ret_transform_in_memory_data
                          ) as patched_transform_in_memory_data:

            with patch.object(fixture_omf.PIServerNorthPlugin,
                              'create_omf_objects',
                              return_value=mock_async_call()
                              ) as patched_create_omf_objects:

                with patch.object(fixture_omf.PIServerNorthPlugin,
                                  'send_in_memory_data_to_picromf',
                                  side_effect=KeyError('mocked object generated an exception')
                                  ) as patched_send_in_memory_data_to_picromf:

                    with patch.object(fixture_omf.PIServerNorthPlugin,
                                      'deleted_omf_types_already_created',
                                      return_value=mock_async_call()
                                      ) as patched_deleted_omf_types_already_created:

                        with pytest.raises(Exception):
                            data_sent, new_position, num_sent = await fixture_omf.plugin_send(data, p_raw_data,
                                                                                              _STREAM_ID)

        if ret_transform_in_memory_data[0]:
            # data_available

            assert patched_transform_in_memory_data.calles
            assert patched_create_omf_objects.called
            assert patched_send_in_memory_data_to_picromf.called
            assert patched_deleted_omf_types_already_created.called

    def test_plugin_shutdown(self):

        pi_server._logger = MagicMock()
        data = []
        pi_server.plugin_shutdown([data])

    def test_plugin_reconfigure(self):

        pi_server._logger = MagicMock()
        pi_server.plugin_reconfigure()


class TestPIServerNorthPlugin:
    """Unit tests related to PIServerNorthPlugin, methods used internally to the plugin"""

    @pytest.mark.parametrize(
        "p_configuration_key, "
        "p_type_id, "
        "p_data_from_storage, "
        "expected_data, ",
        [

            # Case 1
            (
                    # p_configuration_key
                    "SEND_PR1",

                    # p_type_id
                    "0001",

                    # p_data_from_storage
                    {
                        "rows":
                            [

                                {
                                    "configuration_key": "SEND_PR1",
                                    "type_id": "0001",
                                    "asset_code": "asset_code_1"
                                },
                                {
                                    "configuration_key": "SEND_PR1",
                                    "type_id": "0001",
                                    "asset_code": "asset_code_2"
                                }

                            ]
                    },

                    # expected_data
                    [
                        "asset_code_1",
                        "asset_code_2"
                    ]
            )
        ]
    )
    @pytest.mark.asyncio
    async def test_retrieve_omf_types_already_created(
            self,
            p_configuration_key,
            p_type_id,
            p_data_from_storage,
            expected_data,
            fixture_omf_north
    ):
        """ Unit test for - _retrieve_omf_types_already_created - successful case """

        _payload_builder = MagicMock(spec=payload_builder)

        @pytest.mark.asyncio
        async def mock_query_tbl_with_payload():
            """ mock _query_tbl_with_payload """

            return p_data_from_storage

        with patch.object(_payload_builder, 'PayloadBuilder', return_value=True):
            with patch.object(fixture_omf_north._sending_process_instance._storage_async,
                              'query_tbl_with_payload',
                              return_value=mock_query_tbl_with_payload()):

                retrieved_rows = await fixture_omf_north._retrieve_omf_types_already_created(p_configuration_key, p_type_id)

        assert retrieved_rows == expected_data

    @pytest.mark.parametrize(
        "p_asset_code, "
        "expected_asset_code, ",
        [
            # p_asset_code   # expected_asset_code
            ("asset_code_1 ",  "asset_code_1"),
            (" asset_code_2 ", "asset_code_2"),
            ("asset_ code_3",  "asset_code_3"),
        ]
    )
    def test_generate_omf_asset_id(
            self,
            p_asset_code,
            expected_asset_code,
            fixture_omf_north
    ):
        """Tests _generate_omf_asset_id """

        generated_asset_code = fixture_omf_north._generate_omf_asset_id(p_asset_code)

        assert generated_asset_code == expected_asset_code

    @pytest.mark.parametrize(
        "p_type_id, "
        "p_asset_code, "
        "expected_measurement_id, ",
        [
            # p_type_id  - p_asset_code    - expected_asset_code
            ("0001",     "asset_code_1 ",  "0001measurement_asset_code_1"),
            ("0002",     " asset_code_2 ", "0002measurement_asset_code_2"),
            ("0003",     "asset_ code_3",  "0003measurement_asset_code_3"),
        ]
    )
    def test_generate_omf_measurement(
            self,
            p_type_id,
            p_asset_code,
            expected_measurement_id,
            fixture_omf_north
    ):
        """Tests _generate_omf_measurement """

        fixture_omf_north._config_omf_types = {"type-id": {"value": p_type_id}}

        generated_measurement_id = fixture_omf_north._generate_omf_measurement(p_asset_code)

        assert generated_measurement_id == expected_measurement_id

    @pytest.mark.parametrize(
        "p_asset_code, "
        "expected_typename, ",
        [
            # p_asset_code     - expected_asset_code
            ("asset_code_1 ",  "asset_code_1_typename"),
            (" asset_code_2 ", "asset_code_2_typename"),
            ("asset_ code_3",  "asset_code_3_typename"),
        ]
    )
    def test_generate_omf_typename_automatic(
            self,
            p_asset_code,
            expected_typename
    ):
        """Tests _generate_omf_typename_automatic """

        sending_process_instance = MagicMock()
        config = []
        config_omf_types = []
        logger = MagicMock()

        omf_north = pi_server.PIServerNorthPlugin(sending_process_instance, config, config_omf_types, logger)

        generated_typename = omf_north._generate_omf_typename_automatic(p_asset_code)

        assert generated_typename == expected_typename

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
                                'Time': {'isindex': True, 'format': 'date-time', 'type': 'string'},
                                'pressure': {'type': 'number', 'format': 'float64'}
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
                                    'lux': {'type': 'number', 'format': 'float64'}
                                },
                                'type': 'object'
                            }
                        ]
                    }

            ),

            # Case 3 - switch / string
            (
                # Origin - Sensor data
                {"asset_code": "switch", "asset_data": {"button": "up"}},

                # type_id
                "0002",

                # Static Data
                {
                    "Location": "Palo Alto",
                    "Company": "Dianomic"
                },

                # Expected
                'switch_typename',
                {
                    'switch_typename':
                    [
                        {
                            'classification': 'static',
                            'id': '0002_switch_typename_sensor',
                            'properties': {
                                'Company': {'type': 'string'},
                                'Name': {'isindex': True, 'type': 'string'},
                                'Location': {'type': 'string'}
                            },
                            'type': 'object'
                        },
                        {
                            'classification': 'dynamic',
                            'id': '0002_switch_typename_measurement',
                            'properties': {
                                'Time': {'isindex': True, 'format': 'date-time', 'type': 'string'},
                                'button': {'type': 'string'}
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
                                                fixture_omf_north
                                            ):
        """ Unit test for - _create_omf_type_automatic - successful case 
            Tests the generation of the OMF messages starting from Asset name and data
            using Automatic OMF Type Mapping
        """

        fixture_omf_north._config_omf_types = {"type-id": {"value": p_type_id}}

        fixture_omf_north._config = {}
        fixture_omf_north._config["StaticData"] = p_static_data
        fixture_omf_north._config["formatNumber"] = "float64"
        fixture_omf_north._config["formatInteger"] = "int64"


        with patch.object(
                            fixture_omf_north,
                            'send_in_memory_data_to_picromf',
                            return_value=mock_async_call()
                          ) as patched_send_in_memory_data_to_picromf:

            typename, omf_type = await fixture_omf_north._create_omf_type_automatic(p_test_data)

        assert typename == expected_typename
        assert omf_type == expected_omf_type

        patched_send_in_memory_data_to_picromf.assert_called_with ("Type", expected_omf_type[expected_typename])

    @pytest.mark.parametrize(
        "p_type_id, "
        "p_asset_code_omf_type, "
        "expected_typename, "
        "expected_omf_type, ",
        [
            # Case 1
            (
                    # p_type_id
                    "0001",

                    # p_asset_code_omf_type
                    {
                        "typename": "position",
                        "static": {
                            "Name": {
                                "type": "string",
                                "isindex": True
                            },
                            "Location": {
                                "type": "string"
                            }
                        },
                        "dynamic": {
                            "Time": {
                                "type": "string",
                                "format": "date-time",
                                "isindex": True
                            },
                            "x": {
                                "type": "number"
                            },
                            "y": {
                                "type": "number"
                            },
                            "z": {
                                "type": "number"
                            }
                        }
                    },

                    # expected_typename
                    "position",

                    # expected_omf_type
                    {
                        "position": [
                            {
                                "id": "0001_position_sensor",
                                "type": "object",
                                "classification": "static",
                                "properties": {
                                    "Name": {
                                        "type": "string",
                                        "isindex": True
                                    },
                                    "Location": {
                                        "type": "string"
                                    }
                                }
                            },
                            {
                                "id": "0001_position_measurement",
                                "type": "object",
                                "classification": "dynamic",
                                "properties": {
                                    "Time": {
                                        "type": "string",
                                        "format": "date-time",
                                        "isindex": True
                                    },
                                    "x": {
                                        "type": "number"
                                    },
                                    "y": {
                                        "type": "number"
                                    },
                                    "z": {
                                        "type": "number"
                                    }

                                }
                            }

                        ]
                    }
            )
        ]
    )
    @pytest.mark.asyncio
    async def test_create_omf_type_configuration_based(
            self,
            p_type_id,
            p_asset_code_omf_type,
            expected_typename,
            expected_omf_type,
            fixture_omf_north
    ):
        """ Unit test for - _create_omf_type_configuration_based - successful case
            Tests the generation of the OMF messages using Configuration Based OMF Type Mapping
        """

        fixture_omf_north._config_omf_types = {"type-id": {"value": p_type_id}}

        with patch.object(fixture_omf_north,
                          'send_in_memory_data_to_picromf',
                          return_value=mock_async_call()
                          ) as patched_send_to_picromf:
            generated_typename, \
                generated_omf_type = await fixture_omf_north._create_omf_type_configuration_based(p_asset_code_omf_type)

        assert generated_typename == expected_typename
        assert generated_omf_type == expected_omf_type

        patched_send_to_picromf.assert_any_call("Type", expected_omf_type[expected_typename])


    @pytest.mark.parametrize(
        "p_asset,"
        "p_type_id, "
        "p_static_data, "        
        "p_typename,"
        "p_omf_type, "
        "expected_container, "
        "expected_static_data, "
        "expected_link_data ",
        [
            # Case 1 - pressure / Number
            (
                # p_asset
                {"asset_code": "pressure", "asset_data": {"pressure": 921.6}},

                # type_id
                "0001",

                # Static Data
                {
                    "Location": "Palo Alto",
                    "Company": "Dianomic"
                },

                # p_typename
                'pressure_typename',

                # p_omf_type
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
                                'Time': {'isindex': True, 'format': 'date-time', 'type': 'string'},
                                'pressure': {'type': 'number'}
                            },
                            'type': 'object'
                         }
                    ]
                },

                # expected_container
                [
                    {
                        'typeid': '0001_pressure_typename_measurement',
                        'id': '0001measurement_pressure'
                    }
                ],

                # expected_static_data
                [
                    {
                        'typeid': '0001_pressure_typename_sensor',
                        'values': [
                                    {
                                        'Company': 'Dianomic',
                                        'Location': 'Palo Alto',
                                        'Name': 'pressure'
                                    }
                        ]
                    }
                ],

                # expected_link_data
                [
                    {
                        'typeid': '__Link', 'values': [
                            {
                                    'source': {'typeid': '0001_pressure_typename_sensor', 'index': '_ROOT'},
                                    'target': {'typeid': '0001_pressure_typename_sensor', 'index': 'pressure'}
                            },
                            {
                                    'source': {'typeid': '0001_pressure_typename_sensor', 'index': 'pressure'},
                                    'target': {'containerid': '0001measurement_pressure'}
                            }
                        ]
                     }
                ]
            )

        ]
    )
    @pytest.mark.asyncio
    async def test_create_omf_object_links(
                                        self,
                                        p_asset,
                                        p_type_id,
                                        p_static_data,
                                        p_typename,
                                        p_omf_type,
                                        expected_container,
                                        expected_static_data,
                                        expected_link_data,
                                        fixture_omf_north
    ):

        fixture_omf_north._config_omf_types = {"type-id": {"value": p_type_id}}
        fixture_omf_north._config = {"StaticData": p_static_data}

        with patch.object(fixture_omf_north,
                          'send_in_memory_data_to_picromf',
                          side_effect=[asyncio.ensure_future(mock_async_call()) for x in range(3)]
                          ) as patched_send_to_picromf:

            await fixture_omf_north._create_omf_object_links(p_asset["asset_code"], p_typename, p_omf_type)

        assert patched_send_to_picromf.call_count == 3

        patched_send_to_picromf.assert_any_call("Container", expected_container)
        patched_send_to_picromf.assert_any_call("Data", expected_static_data)
        patched_send_to_picromf.assert_any_call("Data", expected_link_data)

    @pytest.mark.parametrize(
        "p_creation_type, "
        "p_data_origin, "
        "p_asset_codes_already_created, "
        "p_omf_objects_configuration_based ",
        [
            # Case 1 - automatic
            (
                # p_creation_type
                "automatic",

                # Origin
                [
                    {
                        "id": 10,
                        "asset_code": "test_asset_code",
                        "reading": {"humidity": 10, "temperature": 20},
                        "user_ts": '2018-04-20 09:38:50.163164+00'
                    }
                ],

                # asset_codes_already_created
                [
                    "test_none"
                ],

                # omf_objects_configuration_based
                {"none": "none"}
            ),
            # Case 2 - configuration
            (
                    # p_creation_type
                    "configuration",

                    # Origin
                    [
                        {
                            "id": 10,
                            "asset_code": "test_asset_code",
                            "reading": {"humidity": 10, "temperature": 20},
                            "user_ts": '2018-04-20 09:38:50.163164+00'
                        }
                    ],

                    # asset_codes_already_created
                    [
                        "test_none"
                    ],

                    # omf_objects_configuration_based
                    {"test_asset_code": {"value": "test_asset_code"}}
            )

        ]
    )
    @pytest.mark.asyncio
    async def test_create_omf_objects(
                                        self,
                                        p_creation_type,
                                        p_data_origin,
                                        p_asset_codes_already_created,
                                        p_omf_objects_configuration_based,
                                        fixture_omf_north
                                        ):
        """ Unit test for - create_omf_objects - successful case
            Tests the evaluation of the 2 ways of creating OMF objects: automatic or configuration based
        """

        config_category_name = "SEND_PR"
        type_id = "0001"

        fixture_omf_north._config_omf_types = {"type-id": {"value": type_id}}
        fixture_omf_north._config_omf_types = p_omf_objects_configuration_based

        if p_creation_type == "automatic":

            with patch.object(fixture_omf_north,
                              '_retrieve_omf_types_already_created',
                              return_value=mock_async_call(p_asset_codes_already_created)):

                with patch.object(
                        fixture_omf_north,
                        '_create_omf_objects_automatic',
                        return_value=mock_async_call()
                ) as patched_create_omf_objects_automatic:

                    with patch.object(fixture_omf_north,
                                      '_flag_created_omf_type',
                                      return_value=mock_async_call()
                                      ) as patched_flag_created_omf_type:

                        await fixture_omf_north.create_omf_objects(p_data_origin, config_category_name, type_id)

            assert patched_create_omf_objects_automatic.called
            assert patched_flag_created_omf_type.called

        elif p_creation_type == "configuration":

            with patch.object(fixture_omf_north,
                              '_retrieve_omf_types_already_created',
                              return_value=mock_async_call(p_asset_codes_already_created)):

                with patch.object(
                        fixture_omf_north,
                        '_create_omf_objects_configuration_based',
                        return_value=mock_async_call()
                ) as patched_create_omf_objects_configuration_based:

                    with patch.object(fixture_omf_north,
                                      '_flag_created_omf_type',
                                      return_value=mock_async_call()
                                      ) as patched_flag_created_omf_type:
                        await fixture_omf_north.create_omf_objects(p_data_origin, config_category_name, type_id)

            assert patched_create_omf_objects_configuration_based.called
            assert patched_flag_created_omf_type.called
        else:
            raise Exception("ERROR : creation type not defined !")

    @pytest.mark.parametrize(
        "p_key, "
        "p_value, "
        "expected, ",
        [
            # Good cases
            ('producerToken', "xxx", "good"),

            # Bad cases
            ('NO-producerToken', "", "exception"),
            ('producerToken', "", "exception")
        ]
    )
    def test_validate_configuration(
                                    self,
                                    p_key,
                                    p_value,
                                    expected):
        """ Tests the validation of the configurations retrieved from the Configuration Manager
            handled by _validate_configuration """

        pi_server._logger = MagicMock()

        data = {p_key: {'value': p_value}}

        if expected == "good":
            assert not pi_server._logger.error.called

        elif expected == "exception":
            with pytest.raises(ValueError):
                pi_server._validate_configuration(data)

            assert pi_server._logger.error.called

    @pytest.mark.parametrize(
        "p_key, "
        "p_value, "
        "expected, ",
        [
            # Good cases
            ('type-id', "xxx", "good"),

            # Bad cases
            ('NO-type-id', "", "exception"),
            ('type-id', "", "exception")
        ]
    )
    def test_validate_configuration_omf_type(
                                    self,
                                    p_key,
                                    p_value,
                                    expected):
        """ Tests the validation of the configurations retrieved from the Configuration Manager
            related to the OMF types """

        pi_server._logger = MagicMock()

        data = {p_key: {'value': p_value}}

        if expected == "good":
            assert not pi_server._logger.error.called

        elif expected == "exception":
            with pytest.raises(ValueError):
                pi_server._validate_configuration_omf_type(data)

            assert pi_server._logger.error.called

    @pytest.mark.parametrize(
        "p_test_data ",
        [
            # Case 1 - pressure / Number
            (
                {
                    'dummy': 'dummy'
                }
            ),

        ]
    )
    @pytest.mark.asyncio
    async def test_send_in_memory_data_to_picromf_success(
                                                self,
                                                p_test_data,
                                                fixture_omf_north):
        """ Unit test for - send_in_memory_data_to_picromf - successful case
            Tests a successful communication
        """

        fixture_omf_north._config = dict(producerToken="dummy_producerToken")
        fixture_omf_north._config["URL"] = "dummy_URL"
        fixture_omf_north._config["OMFRetrySleepTime"] = 1
        fixture_omf_north._config["OMFHttpTimeout"] = 1
        fixture_omf_north._config["OMFMaxRetry"] = 1
        fixture_omf_north._config["compression"] = "false"


        with patch.object(aiohttp.ClientSession,
                          'post',
                          return_value=MockAiohttpClientSessionSuccess()
                          ) as patched_aiohttp:

            await fixture_omf_north.send_in_memory_data_to_picromf("Type", p_test_data)

        assert patched_aiohttp.called
        assert patched_aiohttp.call_count == 1

    @pytest.mark.parametrize(
        "p_is_error, "
        "p_code, "
        "p_text, "
        "p_test_data ",
        [
            (
                False,
                400, 'Invalid value type for the property',
                {'dummy': 'dummy'}
            ),
            (
                False,
                400, 'Redefinition of the type with the same ID is not allowed',
                {'dummy': 'dummy'}
            ),
            (
                True,
                400, 'None',
                {'dummy': 'dummy'}
            ),
            (
                True,
                404, 'None',
                {'dummy': 'dummy'}
            ),
            (
                True,
                404, 'Invalid value type for the property',
                {'dummy': 'dummy'}
            ),

        ]
    )
    @pytest.mark.asyncio
    async def test_send_in_memory_data_to_picromf_success_not_blocking_error(
                                                self,
                                                p_is_error,
                                                p_code,
                                                p_text,
                                                p_test_data,
                                                fixture_omf_north):
        """ Unit test for - send_in_memory_data_to_picromf
            test cases of blocking error (exception raised) and not blocking error
        """

        fixture_omf_north._config = dict(producerToken="dummy_producerToken")
        fixture_omf_north._config["URL"] = "dummy_URL"
        fixture_omf_north._config["OMFRetrySleepTime"] = 1
        fixture_omf_north._config["OMFHttpTimeout"] = 1
        fixture_omf_north._config["OMFMaxRetry"] = 1
        fixture_omf_north._config["compression"] = "false"
        fixture_omf_north._config["notBlockingErrors"] = ast.literal_eval(pi_server._CONFIG_DEFAULT_OMF["notBlockingErrors"]["default"])

        with patch.object(aiohttp.ClientSession,
                          'post',
                          return_value=MockAiohttpClientSession(p_code, p_text)
                          ) as patched_aiohttp:
            if p_is_error:
                # blocking error (exception raised)
                with pytest.raises(Exception):
                    await fixture_omf_north.send_in_memory_data_to_picromf("Data", p_test_data)
            else:
                # not blocking error, operation terminated successfully
                await fixture_omf_north.send_in_memory_data_to_picromf("Data", p_test_data)

        assert patched_aiohttp.called
        # as OMFMaxRetry is set to 1
        assert patched_aiohttp.call_count == 1

    @pytest.mark.parametrize(
        "p_type, "
        "p_test_data ",
        [
            # Case 1 - pressure / Number
            (
                "Type",
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
                                'Time': {'isindex': True, 'format': 'date-time', 'type': 'string'},
                                'pressure': {'type': 'number'}
                            },
                            'type': 'object'
                         }
                    ]
                }

            ),

        ]
    )
    @pytest.mark.asyncio
    async def test_send_in_memory_data_to_picromf_data(
                                                self,
                                                p_type,
                                                p_test_data,
                                                fixture_omf_north):
        """ Unit test for - send_in_memory_data_to_picromf - successful case
            Tests the data sent to the PI Server in relation of an OMF type
        """

        # Values for the test
        test_url = "test_URL"
        test_producer_token = "test_producerToken"
        test_omf_http_timeout = 1
        test_headers = {
                        'producertoken': test_producer_token,
                        'messagetype': p_type,
                        'action': 'create',
                        'messageformat': 'JSON',
                        'omfversion': '1.0'}

        fixture_omf_north._config = dict(producerToken=test_producer_token)
        fixture_omf_north._config["URL"] = test_url
        fixture_omf_north._config["OMFRetrySleepTime"] = 1
        fixture_omf_north._config["OMFHttpTimeout"] = test_omf_http_timeout
        fixture_omf_north._config["OMFMaxRetry"] = 1
        fixture_omf_north._config["compression"] = "false"

        # To avoid the wait time
        with patch.object(time, 'sleep', return_value=True):

            with patch.object(aiohttp.ClientSession,
                              'post',
                              return_value=MockAiohttpClientSessionSuccess()
                              ) as patched_aiohttp:

                await fixture_omf_north.send_in_memory_data_to_picromf(p_type, p_test_data)

        str_data = json.dumps(p_test_data)
        assert patched_aiohttp.call_count == 1
        patched_aiohttp.assert_called_with(
                                            url=test_url,
                                            headers=test_headers,
                                            data=str_data,
                                            timeout=test_omf_http_timeout)

    @pytest.mark.parametrize(
        "p_test_data ",
        [
            # Case 1 - pressure / Number
            (
                {
                    'dummy': 'dummy'
                }

            ),

        ]
    )
    @pytest.mark.asyncio
    async def test_send_in_memory_data_to_picromf_error(
                                                    self,
                                                    p_test_data,
                                                    fixture_omf_north):
        """ Unit test for - send_in_memory_data_to_picromf - successful case
            Tests the behaviour  in case of communication error:
            exception erased,
            message logged
            and number of retries
        """

        max_retry = 3

        fixture_omf_north._config = dict(producerToken="dummy_producerToken")
        fixture_omf_north._config["URL"] = "dummy_URL"
        fixture_omf_north._config["OMFRetrySleepTime"] = 1
        fixture_omf_north._config["OMFHttpTimeout"] = 1
        fixture_omf_north._config["OMFMaxRetry"] = max_retry
        fixture_omf_north._config["compression"] = "false"
        fixture_omf_north._config["notBlockingErrors"] = [{'id': 400, 'message': 'none'}]

        # To avoid the wait time
        with patch.object(time, 'sleep', return_value=True):

            with patch.object(aiohttp.ClientSession,
                              'post',
                              return_value=MockAiohttpClientSessionError()
                              ) as patched_aiohttp:

                # Tests the raising of the exception
                with pytest.raises(Exception):
                    await fixture_omf_north.send_in_memory_data_to_picromf("Type", p_test_data)

        assert patched_aiohttp.call_count == max_retry

    @pytest.mark.parametrize(
        "p_data_origin, "
        "type_id, "
        "expected_data_to_send, "
        "expected_is_data_available, "
        "expected_new_position, "
        "expected_num_sent", [
            # Case 1
            (
                    # Origin
                    [
                        {
                            "id": 10,
                            "asset_code": "test_asset_code",
                            "reading": {"humidity": 11, "temperature": 38},
                            "user_ts": '2018-04-20 09:38:50.163164+00'
                        }
                    ],
                    "0001",
                    # Transformed
                    [
                        {
                            "containerid": "0001measurement_test_asset_code",
                            "values": [
                                {
                                    "Time": "2018-04-20T09:38:50.163Z",
                                    "humidity": 11,
                                    "temperature": 38
                                }
                            ]
                        }
                    ],
                    True, 10, 1
            ),
            # Case 2
            (
                    # Origin
                    [
                        {
                            "id": 11,
                            "asset_code": "test_asset_code",
                            "reading": {"tick": "tock"},
                            "user_ts": '2018-04-20 09:38:50.163164+00'
                        }
                    ],
                    "0001",
                    # Transformed
                    [
                        {
                            "containerid": "0001measurement_test_asset_code",
                            "values": [
                                {
                                    "Time": "2018-04-20T09:38:50.163Z",
                                    "tick": "tock"
                                }
                            ]
                        }
                    ],
                    True, 11, 1
            ),

            # Case 3 - 2 rows
            (
                    # Origin
                    [
                        {
                            "id": 12,
                            "asset_code": "test_asset_code",
                            "reading": {"pressure": 957.2},
                            "user_ts": '2018-04-20 09:38:50.163164+00'
                        },
                        {
                            "id": 20,
                            "asset_code": "test_asset_code",
                            "reading": {"y": 34, "z": 114, "x": -174},
                            "user_ts": '2018-04-20 09:38:50.163164+00'
                        }
                    ],
                    "0001",
                    # Transformed
                    [
                        {
                            "containerid": "0001measurement_test_asset_code",
                            "values": [
                                {
                                    "Time": "2018-04-20T09:38:50.163Z",
                                    "pressure": 957.2
                                }
                            ]
                        },
                        {
                            "containerid": "0001measurement_test_asset_code",
                            "values": [
                                {
                                    "Time": "2018-04-20T09:38:50.163Z",
                                    "y": 34,
                                    "z": 114,
                                    "x": -174,
                                }
                            ]
                        },
                    ],
                    True, 20, 2
            )
    ])
    def test_plugin_transform_in_memory_data(self,
                                             p_data_origin,
                                             type_id,
                                             expected_data_to_send,
                                             expected_is_data_available,
                                             expected_new_position,
                                             expected_num_sent,
                                             fixture_omf_north):
        """Tests the plugin in memory transformations """

        generated_data_to_send = [None for x in range( len(expected_data_to_send) )]

        fixture_omf_north._config_omf_types = {"type-id": {"value": type_id}}

        is_data_available, new_position, num_sent = fixture_omf_north.transform_in_memory_data(generated_data_to_send,
                                                                                       p_data_origin)

        assert generated_data_to_send == expected_data_to_send

        assert is_data_available == expected_is_data_available
        assert new_position == expected_new_position
        assert num_sent == expected_num_sent

