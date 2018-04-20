# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import pytest
import json

from unittest.mock import patch, call, MagicMock


from foglamp.plugins.north.omf import omf
import foglamp.tasks.north.sending_process as module_sp


class TestOMF:
    """Unit tests for the omf plugin"""

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

            # Bad case 1 - StaticData
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

            # Bad case 2 - OMFMaxRetry
            {
                "stream_id": {"value": 1},

                "_CONFIG_CATEGORY_NAME": module_sp.SendingProcess._CONFIG_CATEGORY_NAME,
                "URL": {"value": "test_URL"},
                "producerToken": {"value": "test_producerToken"},
                "OMFMaxRetry": {"value": 100},
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
            }

    ])
    def test_plugin_init_bad(self, data):
        """Tests plugin_init using an invalid set of values"""

        omf._logger = MagicMock()

        with pytest.raises(Exception) as exception_info:
            config = omf.plugin_init(data)


    def test_plugin_send(self):
    # FIXME: todo
        pass

    def test_plugin_shutdown(self):

        omf._logger = MagicMock()
        data = []
        omf.plugin_shutdown([data])

    def test_plugin_reconfigure(self):

        omf._logger = MagicMock()
        omf.plugin_reconfigure()




