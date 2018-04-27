# -*- coding: utf-8 -*-
""" Unit tests for the omf plugin """

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import pytest
import json
import sys

from unittest.mock import patch, MagicMock


from foglamp.plugins.north.omf import omf
import foglamp.tasks.north.sending_process as module_sp


# noinspection PyUnresolvedReferences
@pytest.allure.feature("unit")
@pytest.allure.story("plugin", "north", "omf")
class TestOMF:
    """Unit tests related to the public methods of the omf plugin """

    def test_plugin_info(self):

        assert omf.plugin_info() == {
            'name': "OMF North",
            'version': "1.0.0",
            'type': "north",
            'interface': "1.0",
            'config': omf._CONFIG_DEFAULT_OMF
        }

    def test_plugin_init_good(self):
        """Tests plugin_init using a good set of values"""

        omf._logger = MagicMock()

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

                'sending_process_instance': MagicMock()
            }

        config = omf.plugin_init(data)

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

        omf._logger = MagicMock()

        with pytest.raises(Exception):
            omf.plugin_init(data)

    def test_plugin_send_ok(self):
        """Tests plugin _plugin_send function, case everything went fine """

        def dummy_ok():
            """" """
            return True, 1, 1

        def data_send_ok():
            """" """
            return True

        def omf_types_create():
            """" """
            return True

        omf._logger = MagicMock()
        omf._config_omf_types = {"type-id": {"value": "0001"}}
        data = MagicMock()

        raw_data = []
        stream_id = 1

        # Test good case
        with patch.object(omf.OmfNorthPlugin, 'transform_in_memory_data', return_value=dummy_ok()):
            with patch.object(omf.OmfNorthPlugin, 'create_omf_objects', return_value=dummy_ok()):
                with patch.object(omf.OmfNorthPlugin, 'send_in_memory_data_to_picromf', return_value=data_send_ok()):
                    with patch.object(omf.OmfNorthPlugin, 'deleted_omf_types_already_created',
                                      return_value=omf_types_create()) as mocked_deleted_omf_types_already_created:
                        omf.plugin_send(data, raw_data, stream_id)

        assert not mocked_deleted_omf_types_already_created.called

    def test_plugin_send_bad(self):
        """Tests plugin _plugin_send function,
           it tests especially if the omf objects are created again in case of a communication error
           NOTE : the test will print a message to the stderr containing 'mocked object generated an exception'
                  the message could/should be ignored.
        """

        # noinspection PyPep8Naming
        class to_dev_null(object):
            """ Used to ignore messages sent to the stderr """
            def to_dev_null(self, _data):
                """" """
                pass

        def dummy_ok():
            """" """
            return True, 1, 1

        def omf_types_create():
            """" """
            return True

        omf._logger = MagicMock()
        omf._config_omf_types = {"type-id": {"value": "0001"}}
        data = MagicMock()

        raw_data = []
        stream_id = 1

        # Test bad case - send operation raise an exception
        with patch.object(omf.OmfNorthPlugin, 'transform_in_memory_data', return_value=dummy_ok()):
            with patch.object(omf.OmfNorthPlugin, 'create_omf_objects', return_value=dummy_ok()):
                with patch.object(omf.OmfNorthPlugin, 'send_in_memory_data_to_picromf',
                                  side_effect=KeyError('mocked object generated an exception')):
                    with patch.object(omf.OmfNorthPlugin, 'deleted_omf_types_already_created',
                                      return_value=omf_types_create()) as mocked_deleted_omf_types_already_created:

                        with pytest.raises(Exception):
                            # To ignore messages sent to the stderr
                            sys.stderr = to_dev_null()

                            omf.plugin_send(data, raw_data, stream_id)

                        assert mocked_deleted_omf_types_already_created.called

    def test_plugin_shutdown(self):

        omf._logger = MagicMock()
        data = []
        omf.plugin_shutdown([data])

    def test_plugin_reconfigure(self):

        omf._logger = MagicMock()
        omf.plugin_reconfigure()


class TestOmfNorthPlugin:
    """Unit tests related to OmfNorthPlugin, methods used internally to the plugin"""

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
                                            "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
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
                                                    "Time": "2018-04-20T09:38:50.163164Z",
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
                                                "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
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
                                                        "Time": "2018-04-20T09:38:50.163164Z",
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
                                                "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                                                "reading": {"pressure": 957.2},
                                                "user_ts": '2018-04-20 09:38:50.163164+00'
                                            },
                                            {
                                                "id": 20,
                                                "asset_code": "test_asset_code",
                                                "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
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
                                                        "Time": "2018-04-20T09:38:50.163164Z",
                                                        "pressure": 957.2
                                                    }
                                                ]
                                            },
                                            {
                                                "containerid": "0001measurement_test_asset_code",
                                                "values": [
                                                    {
                                                        "Time": "2018-04-20T09:38:50.163164Z",
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
                                             expected_num_sent):
        """Tests the plugin in memory transformations """

        sending_process_instance = []
        config = []
        config_omf_types = []
        logger = MagicMock()
        generated_data_to_send = []

        omf_north = omf.OmfNorthPlugin(sending_process_instance, config, config_omf_types, logger)

        omf_north._config_omf_types = {"type-id": {"value": type_id}}

        is_data_available, new_position, num_sent = omf_north.transform_in_memory_data(generated_data_to_send,
                                                                                       p_data_origin)

        assert generated_data_to_send == expected_data_to_send

        assert is_data_available == expected_is_data_available
        assert new_position == expected_new_position
        assert num_sent == expected_num_sent

    @pytest.mark.parametrize(
        "p_data_origin, "
        "expected_output ",
        [
            # Case 1
            (
                # Origin
                [
                    {
                        "id": 10,
                        "asset_code": "test_asset_code",
                        "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                        "reading": {"humidity": 10, "temperature": 20},
                        "user_ts": '2018-04-20 09:38:50.163164+00'
                    }
                ]
                , "# FIXME:"
            )
        ]
    )
    def test_create_omf_objects(self, p_data_origin, expected_output):
        # # FIXME:
        """ Test the creation of the OMF objects """

        sending_process_instance = []
        config = []
        config_omf_types = []
        logger = MagicMock()
        generated_data_to_send = []

        config_category_name = "# FIXME:"
        type_id = "0001"

        omf_north = omf.OmfNorthPlugin(sending_process_instance, config, config_omf_types, logger)

        omf_north._config_omf_types = {"type-id": {"value": type_id}}
        # omf_north.create_omf_objects(p_data_origin, config_category_name, type_id)

        assert True


    @pytest.mark.parametrize(
        "p_test_data, "
        "expected_output ",
        [
            # Case 1
            (
                # Origin
                [
                    {
                        "id": 10,
                        "asset_code": "test_asset_code",
                        "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                        "reading": {"humidity": 10, "temperature": 20},
                        "user_ts": '2018-04-20 09:38:50.163164+00'
                    }
                ]
                , "# FIXME:"
            )
        ]
    )
    def test_create_omf_objects_automatic(self, p_test_data, expected_output):
        assert True

    @pytest.mark.parametrize(
        "p_test_data, "
        "expected_output ",
        [
            # Case 1
            (
                # Origin
                [
                    {
                        "id": 10,
                        "asset_code": "test_asset_code",
                        "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                        "reading": {"humidity": 10, "temperature": 20},
                        "user_ts": '2018-04-20 09:38:50.163164+00'
                    }
                ]
                , "# FIXME:"
            )
        ]
    )
    def test_create_omf_type_automatic(self, p_test_data, expected_output):
        # FIXME:

        sending_process_instance = []
        config = []
        config_omf_types = []
        logger = MagicMock()
        generated_data_to_send = []

        config_category_name = "# FIXME:"
        type_id = "0001"

        omf_north = omf.OmfNorthPlugin(sending_process_instance, config, config_omf_types, logger)

        omf_north._config_omf_types = {"type-id": {"value": type_id}}

        omf_north._create_omf_type_automatic(p_test_data)


        assert True


    @pytest.mark.parametrize(
        "p_test_data, "
        "expected_output ",
        [
            # Case 1
            (
                # Origin
                [
                    {
                        "id": 10,
                        "asset_code": "test_asset_code",
                        "read_key": "ef6e1368-4182-11e8-842f-0ed5f89f718b",
                        "reading": {"humidity": 10, "temperature": 20},
                        "user_ts": '2018-04-20 09:38:50.163164+00'
                    }
                ]
                , "# FIXME:"
            )
        ]
    )
    def test_create_omf_object_links(self, p_test_data, expected_output):
        # FIXME:
        assert True