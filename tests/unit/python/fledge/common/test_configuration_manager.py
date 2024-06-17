# -*- coding: utf-8 -*-

import asyncio
import json
import ipaddress
from unittest.mock import MagicMock, patch, call
import pytest
import sys
from fledge.common.configuration_manager import ConfigurationManager, ConfigurationManagerSingleton, \
    _valid_type_strings, _logger, _optional_items
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.audit_logger import AuditLogger


__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

CAT_NAME = 'test'
ITEM_NAME = "test_item_name"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "configuration_manager")
class TestConfigurationManager:
    @pytest.fixture()
    def reset_singleton(self):
        # executed before each test
        ConfigurationManagerSingleton._shared_state = {}
        yield
        ConfigurationManagerSingleton._shared_state = {}

    def test_supported_validate_type_strings(self):
        expected_types = ['IPv4', 'IPv6', 'JSON', 'URL', 'X509 certificate', 'boolean', 'code', 'enumeration',
                          'float', 'integer', 'northTask', 'password', 'script', 'string', 'ACL', 'bucket',
                          'list', 'kvlist']
        assert len(expected_types) == len(_valid_type_strings)
        assert sorted(expected_types) == _valid_type_strings

    def test_supported_optional_items(self):
        expected_types = ['deprecated', 'displayName', 'group', 'length', 'mandatory', 'maximum', 'minimum', 'order',
                          'readonly', 'rule', 'validity', 'listSize', 'listName']
        assert len(expected_types) == len(_optional_items)
        assert sorted(expected_types) == _optional_items

    def test_constructor_no_storage_client_defined_no_storage_client_passed(
            self, reset_singleton):
        # first time initializing ConfigurationManager without storage client
        # produces error
        with pytest.raises(TypeError) as excinfo:
            ConfigurationManager()
        assert 'Must be a valid Storage object' in str(excinfo.value)

    def test_constructor_no_storage_client_defined_storage_client_passed(
            self, reset_singleton):
        # first time initializing ConfigurationManager with storage client
        # works
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        assert hasattr(c_mgr, '_storage')
        assert isinstance(c_mgr._storage, StorageClientAsync)
        assert hasattr(c_mgr, '_registered_interests')

    def test_constructor_storage_client_defined_storage_client_passed(
            self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        # second time initializing ConfigurationManager with new storage client
        # works
        storage_client_mock2 = MagicMock(spec=StorageClientAsync)
        c_mgr2 = ConfigurationManager(storage_client_mock2)
        assert hasattr(c_mgr2, '_storage')
        # ignore new storage client
        assert isinstance(c_mgr2._storage, StorageClientAsync)
        assert hasattr(c_mgr2, '_registered_interests')

    def test_constructor_storage_client_defined_no_storage_client_passed(
            self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        # second time initializing ConfigurationManager without storage client
        # works
        c_mgr2 = ConfigurationManager()
        assert hasattr(c_mgr2, '_storage')
        assert isinstance(c_mgr2._storage, StorageClientAsync)
        assert hasattr(c_mgr2, '_registered_interests')
        assert 0 == len(c_mgr._registered_interests)

    def test_register_interest_no_category_name(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with pytest.raises(ValueError) as excinfo:
            c_mgr.register_interest(None, 'callback')
        assert 'Failed to register interest. category_name cannot be None' in str(
            excinfo.value)

    def test_register_interest_no_callback(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with pytest.raises(ValueError) as excinfo:
            c_mgr.register_interest('name', None)
        assert 'Failed to register interest. callback cannot be None' in str(
            excinfo.value)

    def test_register_interest(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        c_mgr.register_interest('name', 'callback')
        assert 'callback' in c_mgr._registered_interests['name']
        assert 1 == len(c_mgr._registered_interests)

    def test_unregister_interest_no_category_name(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with pytest.raises(ValueError) as excinfo:
            c_mgr.unregister_interest(None, 'callback')
        assert 'Failed to unregister interest. category_name cannot be None' in str(
            excinfo.value)

    def test_unregister_interest_no_callback(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with pytest.raises(ValueError) as excinfo:
            c_mgr.unregister_interest('name', None)
        assert 'Failed to unregister interest. callback cannot be None' in str(
            excinfo.value)

    def test_unregister_interest(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        c_mgr.register_interest('name', 'callback')
        assert 1 == len(c_mgr._registered_interests)
        c_mgr.unregister_interest('name', 'callback')
        assert len(c_mgr._registered_interests) is 0

    async def test__run_callbacks(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        c_mgr.register_interest('name', 'configuration_manager_callback')
        await c_mgr._run_callbacks('name')

    async def test__run_callbacks_invalid_module(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        c_mgr.register_interest('name', 'invalid')
        with patch.object(_logger, "error") as log_error:
            with pytest.raises(Exception) as excinfo:
                await c_mgr._run_callbacks('name')
            import sys
            if sys.version_info[1] >= 6:
                assert excinfo.type is ModuleNotFoundError
            else:
                assert excinfo.type is ImportError
            assert "No module named 'invalid'" == str(excinfo.value)
        assert 1 == log_error.call_count
        log_error.assert_called_once_with('Unable to import callback module %s for category_name %s', 'invalid',
                                          'name', exc_info=True)

    async def test__run_callbacks_norun(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        c_mgr.register_interest('name', 'configuration_manager_callback_norun')
        with patch.object(_logger, "error") as log_error:
            with pytest.raises(Exception) as excinfo:
                await c_mgr._run_callbacks('name')
            assert excinfo.type is AttributeError
            assert 'Callback module configuration_manager_callback_norun does not have method run' in str(
                excinfo.value)
        assert 1 == log_error.call_count
        log_error.assert_called_once_with('Callback module %s does not have method run',
                                          'configuration_manager_callback_norun', exc_info=True)

    async def test__run_callbacks_nonasync(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        c_mgr.register_interest(
            'name', 'configuration_manager_callback_nonasync')
        with patch.object(_logger, "error") as log_error:
            with pytest.raises(Exception) as excinfo:
                await c_mgr._run_callbacks('name')
            assert excinfo.type is AttributeError
            assert 'Callback module configuration_manager_callback_nonasync run method must be a coroutine function' in\
                   str(excinfo.value)
        assert 1 == log_error.call_count
        log_error.assert_called_once_with('Callback module %s run method must be a coroutine function',
                                          'configuration_manager_callback_nonasync', exc_info=True)

    async def test__validate_category_val_valid_config_use_default_val(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config = {
            ITEM_NAME: {
                "description": "test description val",
                "type": "string",
                "default": "test default val"
            },
        }
        c_return_value = await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                                            set_value_val_from_default_val=True)
        assert isinstance(c_return_value, dict)
        assert len(c_return_value) is 1
        test_item_val = c_return_value.get(ITEM_NAME)
        assert isinstance(test_item_val, dict)
        assert len(test_item_val) is 4
        assert test_item_val.get("description") is "test description val"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val"
        assert test_item_val.get("value") is "test default val"

        # deep copy check to make sure test_config wasn't modified in the
        # method call
        assert test_config is not c_return_value
        assert isinstance(test_config, dict)
        assert len(test_config) is 1
        test_item_val = test_config.get(ITEM_NAME)
        assert isinstance(test_item_val, dict)
        assert len(test_item_val) is 3
        assert test_item_val.get("description") is "test description val"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val"

    async def test__validate_category_val_invalid_config_use_default_val(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config = {
            ITEM_NAME: {
                "description": "test description val",
                "type": "IPv4",
                "default": "test default val",
                "displayName": "{}"
            },
        }

        with pytest.raises(Exception) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                               set_value_val_from_default_val=True)
        assert excinfo.type is ValueError
        assert "For {} category, unrecognized value for item name {}".format(
            CAT_NAME, ITEM_NAME) == str(excinfo.value)

    async def test__validate_category_val_valid_config_use_value_val(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config = {
            ITEM_NAME: {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                "value": "test value val"
            },
        }
        c_return_value = await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                                            set_value_val_from_default_val=False)
        assert isinstance(c_return_value, dict)
        assert len(c_return_value) is 1
        test_item_val = c_return_value.get(ITEM_NAME)
        assert isinstance(test_item_val, dict)
        assert len(test_item_val) is 4
        assert test_item_val.get("description") is "test description val"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val"
        assert test_item_val.get("value") is "test value val"
        # deep copy check to make sure test_config wasn't modified in the
        # method call
        assert test_config is not c_return_value
        assert isinstance(test_config, dict)
        assert len(test_config) is 1
        test_item_val = test_config.get(ITEM_NAME)
        assert isinstance(test_item_val, dict)
        assert len(test_item_val) is 4
        assert test_item_val.get("description") is "test description val"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val"
        assert test_item_val.get("value") is "test value val"

    async def test__validate_category_optional_attributes_and_use_value(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config = {
            ITEM_NAME: {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                "value": "test value val",
                "readonly": "false",
                "length": "100"
            },
        }
        c_return_value = await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                                            set_value_val_from_default_val=False)
        assert isinstance(c_return_value, dict)
        assert len(c_return_value) is 1
        test_item_val = c_return_value.get(ITEM_NAME)
        assert isinstance(test_item_val, dict)
        assert 6 == len(test_item_val) is 6
        assert "test description val" == test_item_val.get("description")
        assert "string" == test_item_val.get("type")
        assert "test default val" == test_item_val.get("default")
        assert "test value val" == test_item_val.get("value")
        assert "false" == test_item_val.get("readonly")
        assert "100" == test_item_val.get("length")

        # deep copy check to make sure test_config wasn't modified in the
        # method call
        assert test_config is not c_return_value
        assert isinstance(test_config, dict)
        assert len(test_config) is 1
        test_item_val = test_config.get(ITEM_NAME)
        assert isinstance(test_item_val, dict)
        assert 6 == len(test_item_val) is 6
        assert "test description val" == test_item_val.get("description")
        assert "string" == test_item_val.get("type")
        assert "test default val" == test_item_val.get("default")
        assert "test value val" == test_item_val.get("value")
        assert "false" == test_item_val.get("readonly")
        assert "100" == test_item_val.get("length")

    async def test__validate_category_optional_attributes_and_use_default_val(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config = {
            ITEM_NAME: {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                "readonly": "false",
                "length": "100"
            },
        }
        c_return_value = await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                                            set_value_val_from_default_val=True)
        assert isinstance(c_return_value, dict)
        assert 1 == len(c_return_value)
        test_item_val = c_return_value.get(ITEM_NAME)
        assert isinstance(test_item_val, dict)
        assert 6 == len(test_item_val)
        assert "test description val" == test_item_val.get("description")
        assert "string" == test_item_val.get("type")
        assert "test default val" == test_item_val.get("default")
        assert "test default val" == test_item_val.get("value")
        assert "false" == test_item_val.get("readonly")
        assert "100" == test_item_val.get("length")

        # deep copy check to make sure test_config wasn't modified in the
        # method call
        assert test_config is not c_return_value
        assert isinstance(test_config, dict)
        assert 1 == len(test_config)
        test_item_val = test_config.get(ITEM_NAME)
        assert isinstance(test_item_val, dict)
        assert 5 == len(test_item_val)
        assert "test description val" == test_item_val.get("description")
        assert "string" == test_item_val.get("type")
        assert "test default val" == test_item_val.get("default")
        assert "false" == test_item_val.get("readonly")
        assert "100" == test_item_val.get("length")

    @pytest.mark.parametrize("config, item_name, message", [
        ({
             ITEM_NAME: {
                 "description": "test description val",
                 "type": "string",
                 "default": "test default val",
                 "readonly": "unexpected",
             },
         }, "readonly", "boolean"),
        ({
             ITEM_NAME: {
                 "description": "test description val",
                 "type": "string",
                 "default": "test default val",
                 "order": "unexpected",
             },
         }, "order", "an integer"),
        ({
             ITEM_NAME: {
                 "description": "test description val",
                 "type": "string",
                 "default": "test default val",
                 "length": "unexpected",
             },
         }, "length", "an integer"),
        ({
             ITEM_NAME: {
                 "description": "test description val",
                 "type": "float",
                 "default": "test default val",
                 "minimum": "unexpected",
             },
         }, "minimum", "an integer or float"),
        ({
             ITEM_NAME: {
                 "description": "test description val",
                 "type": "integer",
                 "default": "test default val",
                 "maximum": "unexpected",
             },
         }, "maximum", "an integer or float"),
        ({
             ITEM_NAME: {
                 "description": "test description val",
                 "type": "string",
                 "default": "test default val",
                 "mandatory": "1",
             },
         }, "mandatory", "boolean")
    ])
    async def test__validate_category_val_optional_attributes_unrecognized_entry_name(self, config, item_name, message):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with pytest.raises(Exception) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=config,
                                               set_value_val_from_default_val=True)
        assert excinfo.type is ValueError
        assert "For {} category, entry value must be {} for item name {}; got <class 'str'>".format(
            CAT_NAME, message, item_name) == str(excinfo.value)

    async def test__validate_category_val_config_without_value_use_value_val(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config = {
            ITEM_NAME: {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
            },
        }
        with pytest.raises(ValueError) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                               set_value_val_from_default_val=False)
        assert 'For {} category, missing entry name value for item name {}'.format(
            CAT_NAME, ITEM_NAME) == str(excinfo.value)

    async def test__validate_category_val_config_not_dictionary(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        cat_name = 'blah'
        test_config = ()
        with pytest.raises(TypeError) as excinfo:
            await c_mgr._validate_category_val(category_name=cat_name, category_val=test_config,
                                               set_value_val_from_default_val=False)
        assert 'For {} category, category value must be a dictionary; got {}'.format(
            cat_name, type(test_config)) == str(excinfo.value)

    async def test__validate_category_val_item_name_not_string(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        config_item = 5
        test_config = {
            config_item: {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
            },
        }
        with pytest.raises(TypeError) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                               set_value_val_from_default_val=False)
        assert 'For {} category, item name {} must be a string; got {}'.format(
            CAT_NAME, config_item, type(config_item)) == str(excinfo.value)

    async def test__validate_category_val_item_value_not_dictionary(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        item_name = 'test_item_name'
        test_config = {
            item_name: ()
        }
        with pytest.raises(TypeError) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                               set_value_val_from_default_val=False)
        assert 'For {} category, item value must be a dict for item name {}; got {}'.format(
            CAT_NAME, item_name, type(test_config[item_name])) == str(excinfo.value)

    async def test__validate_category_val_config_entry_name_not_string(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        entry_name = 5
        item_name = 'test_item_name'
        test_config = {
            item_name: {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                entry_name: "bla"
            }
        }
        with pytest.raises(TypeError) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                               set_value_val_from_default_val=False)
        assert 'For {} category, entry name {} must be a string for item name {}; got {}'.format(
            CAT_NAME, entry_name, item_name, type(entry_name)) == str(excinfo.value)

    async def test__validate_category_val_config_entry_val_not_string(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        entry_name = 'something'
        entry_value = 5
        item_name = 'test_item_name'
        test_config = {
            item_name: {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                entry_name: entry_value
            },
        }
        with pytest.raises(TypeError) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                               set_value_val_from_default_val=False)
        assert 'For {} category, entry value must be a string for item name {} ' \
               'and entry name {}; got {}'.format(CAT_NAME, item_name, entry_name, type(entry_value)) == str(excinfo.value)

    @pytest.mark.parametrize("config, exception_name, exception_msg", [
        ({"description": "test description", "type": "enumeration", "default": "A"},
         KeyError, "'For test category, options required for enumeration type'"),
        ({"description": "test description", "type": "enumeration", "default": "A", "options": ""},
         TypeError, "For test category, entry value must be a list for item name test_item_name and entry name options; got <class 'str'>"),
        ({"description": "test description", "type": "enumeration", "default": "A", "options": []},
         ValueError, "For test category, entry value cannot be empty list for item_name test_item_name and entry_name options; got []"),
        ({"description": "test description", "type": "enumeration", "default": "C", "options": ["A", "B"]},
         ValueError, "For test category, entry value does not exist in options list for item name test_item_name and entry_name options; got C"),
        ({"description": 1, "type": "enumeration", "default": "A", "options": ["A", "B"]},
         TypeError, "For test category, entry value must be a string for item name test_item_name and entry name description; got <class 'int'>")
    ])
    async def test__validate_category_val_enum_type_bad(self, config, exception_name, exception_msg):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config = {ITEM_NAME: config}
        with pytest.raises(Exception) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                               set_value_val_from_default_val=False)
        assert excinfo.type is exception_name
        assert exception_msg == str(excinfo.value)

    @pytest.mark.skip(reason="FOGL-8281")
    @pytest.mark.parametrize("config", [
    ({ITEM_NAME: {"description": "test description", "type": "bucket", "default": "A"}}),
    ({ITEM_NAME: {"description": "test description", "type": "bucket", "default": "A", "properties": "{}"}}),
    ({"item": {"description": "test description", "type": "string", "default": "A"},
      ITEM_NAME: {"description": "test description", "type": "bucket", "default": "A"}}),
    ])
    async def test__validate_category_val_bucket_type_good(self, config):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        c_return_value = await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=config,
                                               set_value_val_from_default_val=True)
        assert isinstance(c_return_value, dict)

    @pytest.mark.parametrize("config, exc_name, reason", [
        ({ITEM_NAME: {"description": "test description", "type": "bucket", "default": "A"}}, KeyError,
         "'For {} category, properties KV pair must be required for item name {}.'".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test description", "type": "bucket", "default": "A", "property": '{"a": 1}'}},
         KeyError, "'For {} category, properties KV pair must be required for item name {}.'".format(
            CAT_NAME, ITEM_NAME)),
        ({"item": {"description": "test description", "type": "string", "default": "A", "value": "B"},
          ITEM_NAME: {"description": "test description", "type": "bucket", "default": "A"}}, KeyError,
         "'For {} category, properties KV pair must be required for item name {}.'".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test description", "type": "bucket", "default": "A", "properties": '{"a": 1}'}},
         ValueError, "For {} category, properties must be JSON object for item name {}; got <class 'str'>".format(
            CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test description", "type": "bucket", "default": "A", "properties": {}}},
         ValueError, "For {} category, properties JSON object cannot be empty for item name {}".format(
            CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test description", "type": "bucket", "default": "A", "properties": {"k": "v"}}},
         ValueError, "For {} category, key KV pair must exist in properties for item name {}".format(
            CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test description", "type": "bucket", "default": {}, "properties": {"key": "v"}}},
         TypeError, "For {} category, entry value must be a string for item name {} and entry name default; "
                    "got <class 'dict'>".format(CAT_NAME, ITEM_NAME))
    ])
    async def test__validate_category_val_bucket_type_bad(self, config, exc_name, reason):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with pytest.raises(Exception) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=config,
                                               set_value_val_from_default_val=False)
        assert excinfo.type is exc_name
        assert reason == str(excinfo.value)

    @pytest.mark.parametrize("config, exc_name, reason", [
        ({ITEM_NAME: {"description": "test description", "type": "list", "default": "A"}}, KeyError,
         "'For {} category, items KV pair must be required for item name {}.'".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test description", "type": "list", "default": "A", "items": []}}, TypeError,
         "For {} category, entry value must be a string for item name {} and entry name items; "
         "got <class 'list'>".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test description", "type": "list", "default": "A", "items": "str"}}, ValueError,
         "For {} category, items value should either be in string, float, integer, object or enumeration for "
         "item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test description", "type": "list", "default": "A", "items": "float"}}, TypeError,
         "For {} category, default value should be passed array list in string format for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"AJ\"]", "items": "float"}}, ValueError,
        "For {} category, all elements should be of same <class 'float'> type in default value for item name {}".format(
            CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"13\", \"AJ\"]", "items": "integer"}},
         ValueError, "For {} category, all elements should be of same <class 'int'> type in default "
                     "value for item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"13\", \"1.04\"]", "items": "integer"}},
         ValueError, "For {} category, all elements should be of same <class 'int'> type in default "
                     "value for item name {}".format(CAT_NAME, ITEM_NAME)),
        ({"include": {"description": "multiple", "type": "list", "default": "[\"135\", \"1111\"]", "items": "integer",
                      "value": "1"},
        ITEM_NAME: {"description": "test", "type": "list", "default": "[\"13\", \"1\"]", "items": "float"}},
         ValueError, "For {} category, all elements should be of same <class 'float'> type in default "
                     "value for item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[]", "items": "float", "listSize": 1}},
         TypeError, "For {} category, listSize type must be a string for item name {}; got <class 'int'>".format(
            CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[]", "items": "float", "listSize": ""}},
         ValueError, "For {} category, listSize value must be an integer value for item name {}".format(
            CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"10.12\", \"0.9\"]", "items": "float",
                      "listSize": "1"}}, ValueError, "For {} category, default value array list size limit to 1 for "
                                                     "item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"1\"]", "items": "integer",
                      "listSize": "0"}}, ValueError, "For {} category, default value array list size limit to 0 "
                                                     "for item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"6e7777\", \"1.79e+308\", \"1.0\", \"0.9\"]",
                      "items": "float", "listSize": "3"}}, ValueError,
         "For {} category, default value array list size limit to 3 for item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"1\", \"2\", \"1\"]", "items": "integer",
                      "listSize": "3"}}, ValueError, "For {} category, default value array elements are not unique "
                                                     "for item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"a\", \"b\", \"ab\", \"a\"]",
                      "items": "string"}}, ValueError, "For {} category, default value array elements are not unique "
                                                     "for item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "{\"key\": \"1.0\"}", "items": "object",
                      "property": {}}}, KeyError, "'For {} category, properties KV pair must be required for item name "
                                                  "{}'".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "{\"key\": \"1.0\"}", "items": "object",
                      "properties": 1}}, ValueError,
         "For {} category, properties must be JSON object for item name {}; got <class 'int'>".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "{\"key\": \"1.0\"}", "items": "object",
                      "properties": ""}}, ValueError,
         "For {} category, properties must be JSON object for item name {}; got <class 'str'>".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "{\"key\": \"1.0\"}", "items": "object",
                      "properties": {}}}, ValueError,
         "For {} category, properties JSON object cannot be empty for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"integer\"]",
                      "items": "enumeration"}}, KeyError,
         "'For {} category, options required for item name {}'".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"integer\"]",
                      "items": "enumeration", "options": 1}}, TypeError,
         "For {} category, entry value must be a list for item name {} and entry name items; got <class 'int'>".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"integer\"]",
                      "items": "enumeration", "options": []}}, ValueError,
         "For {} category, options cannot be empty list for item_name {} and entry_name items".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"integer\"]",
                      "items": "enumeration", "options": ["integer"], "listSize": 1}}, TypeError,
         "For {} category, listSize type must be a string for item name {}; got <class 'int'>".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"integer\"]",
                      "items": "enumeration", "options": ["integer"], "listSize": "blah"}}, ValueError,
         "For {} category, listSize value must be an integer value for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"integer\"]",
                      "items": "enumeration", "options": ["int"], "listSize": "1"}}, ValueError,
         "For {} category, integer value does not exist in options for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"0\"]",
                      "items": "enumeration", "options": ["999"], "listSize": "1"}}, ValueError,
         "For {} category, 0 value does not exist in options for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"0\"]",
                      "items": "integer", "listSize": "1", "listName": 2}}, TypeError,
         "For {} category, listName type must be a string for item name {}; got <class 'int'>".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "[\"0\"]",
                      "items": "string", "listSize": "1", "listName": ""}}, ValueError,
         "For {} category, listName cannot be empty for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "test", "type": "list", "default": "{\"key\": \"1.0\"}", "items": "object",
                      "properties": {"width": {"description": "", "default": "", "type": ""}}, "listName": ""}},
         ValueError,"For {} category, listName cannot be empty for item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "A"}}, KeyError,
         "'For {} category, items KV pair must be required for item name {}.'".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "A", "items": []}}, TypeError,
         "For {} category, entry value must be a string for item name {} and entry name items; "
         "got <class 'list'>".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "A", "items": "str"}}, ValueError,
         "For {} category, items value should either be in string, float, integer, object or enumeration for "
         "item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "A", "items": "string"}}, TypeError,
         "For {} category, default value should be passed KV pair list in string format for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key\"}", "items": "string"}},
         TypeError, "For {} category, KV pair invalid in default value for item name {}".format(
            CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key\": \"1\"}", "items": "float"}},
         ValueError, "For {} category, all elements should be of same <class 'float'> type in default value for "
                     "item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key\": \"AJ\"}",
                      "items": "integer"}}, ValueError,
         "For {} category, all elements should be of same <class 'int'> type in default value for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key1\": \"13\", \"key2\": \"1.04\"}"
            , "items": "integer"}}, ValueError, "For {} category, all elements should be of same <class 'int'> type in "
                                                "default value for item name {}".format(CAT_NAME, ITEM_NAME)),
        ({"include": {"description": "expression", "type": "kvlist",
                      "default": "{\"key1\": \"135\", \"key2\": \"1111\"}", "items": "integer", "value": "1"},
          ITEM_NAME: {"description": "expression", "type": "kvlist",
                      "default": "{\"key1\": \"135\", \"key2\": \"1111\"}", "items": "float"}}, ValueError,
         "For {} category, all elements should be of same <class 'float'> type in default value for item name "
         "{}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "[]", "items": "float", "listSize": 1}},
         TypeError, "For {} category, listSize type must be a string for item name {}; got <class 'int'>".format(
            CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "[]", "items": "float",
                      "listSize": "blah"}}, ValueError, "For {} category, listSize value must be an integer value for "
                                                        "item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "[\"1\"]", "items": "float",
                      "listSize": "1"}}, TypeError, "For {} category, KV pair invalid in default value for item name "
                                                    "{}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"1\"}", "items": "float",
                      "listSize": "1"}}, TypeError, "For {} category, KV pair invalid in default value for item name "
                                                    "{}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key\": {} }", "items": "float",
                      "listSize": "1"}}, ValueError, "For {} category, all elements should be of same <class 'float'> "
                                                     "type in default value for item name {}".format(
            CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist",
                      "default": "{\"key\": \"1.0\", \"key2\": \"val2\"}", "items": "float", "listSize": "1"}},
         ValueError, "For {} category, default value KV pair list size limit to 1 for item name {}".format(
            CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist",
                      "default": "{\"key\": \"1.0\", \"key\": \"val2\"}", "items": "float", "listSize": "2"}},
         ValueError, "For category {}, duplicate KV pair found for item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist",
                      "default": "{\"key\": \"1.0\", \"key1\": \"val2\"}", "items": "float", "listSize": "2"}},
         ValueError, "For {} category, all elements should be of same <class 'float'> type in default value for "
                     "item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist",
                      "default": "{\"key\": \"1.0\", \"key1\": \"val2\", \"key3\": \"val2\"}", "items": "float",
                      "listSize": "2"}}, ValueError, "For {} category, default value KV pair list size limit to 2 for"
                                                     " item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key\": \"1.0\"}", "items": "float",
                      "listSize": "0"}}, ValueError, "For {} category, default value KV pair list size limit to 0 "
                                                     "for item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key\": \"1.0\"}", "items": "object"
                      }}, KeyError, "'For {} category, properties KV pair must be required for item name {}'".format(
            CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key\": \"1.0\"}", "items": "object",
                      "property": {}}}, KeyError, "'For {} category, properties KV pair must be required for item name "
                                                  "{}'".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key\": \"1.0\"}", "items": "object",
                      "properties": 1}}, ValueError,
         "For {} category, properties must be JSON object for item name {}; got <class 'int'>".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key\": \"1.0\"}", "items": "object",
                      "properties": ""}}, ValueError,
         "For {} category, properties must be JSON object for item name {}; got <class 'str'>".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key\": \"1.0\"}", "items": "object",
                      "properties": {}}}, ValueError,
         "For {} category, properties JSON object cannot be empty for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key\": \"1.0\"}", "items": "object",
                      "properties": {"width": 1}}}, TypeError,
         "For {} category, Properties must be a JSON object for width key for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"width\": \"12\"}", "items":
            "object", "properties": {"width": {}}}}, ValueError,
         "For {} category, width properties cannot be empty for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"width\": \"12\"}", "items":
            "object","properties": {"width": {"type": ""}}}}, ValueError,
        "For {} category, width properties must have type, description, default keys for item name {}".format(
            CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"width\": \"12\"}", "items":
            "object", "properties": {"width": {"description": ""}}}}, ValueError,
         "For {} category, width properties must have type, description, default keys for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"width\": \"12\"}", "items":
            "object", "properties": {"width": {"default": ""}}}}, ValueError,
         "For {} category, width properties must have type, description, default keys for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"width\": \"12\"}", "items":
            "object", "properties": {"width": {"type": "", "description": ""}}}}, ValueError,
         "For {} category, width properties must have type, description, default keys for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"width\": \"12\"}", "items":
            "object", "properties": {"width": {"type": "", "default": ""}}}}, ValueError,
         "For {} category, width properties must have type, description, default keys for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"width\": \"12\"}", "items":
            "object", "properties": {"width": {"description": "", "default": ""}}}}, ValueError,
         "For {} category, width properties must have type, description, default keys for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key1\": \"integer\"}",
                      "items": "enumeration"}}, KeyError,
         "'For {} category, options required for item name {}'".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key1\": \"integer\"}",
                      "items": "enumeration", "options": 1}}, TypeError,
         "For {} category, entry value must be a list for item name {} and entry name items; got <class 'int'>".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key1\": \"integer\"}",
                      "items": "enumeration", "options": []}}, ValueError,
         "For {} category, options cannot be empty list for item_name {} and entry_name items".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key1\": \"integer\"}",
                      "items": "enumeration", "options": ["integer"], "listSize": 1}}, TypeError,
         "For {} category, listSize type must be a string for item name {}; got <class 'int'>".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key1\": \"integer\"}",
                      "items": "enumeration", "options": ["integer"], "listSize": "blah"}}, ValueError,
         "For {} category, listSize value must be an integer value for item name {}".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key1\": \"int\"}",
                      "items": "enumeration", "options": ["integer"], "listSize": "1"}}, ValueError,
         "For {} category, int value does not exist in options for item name {} and entry_name key1".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key1\": \"1\"}",
                      "items": "enumeration", "options": ["integer", "2"], "listSize": "1"}}, ValueError,
         "For {} category, 1 value does not exist in options for item name {} and entry_name key1".format(
             CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key1\": \"1\"}",
                      "items": "enumeration", "options": ["integer", "2"], "listSize": "1", "listName": 1}},
         TypeError, "For {} category, listName type must be a string for item name {}; got <class 'int'>".format(
            CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"key1\": \"1\"}",
                      "items": "enumeration", "options": ["integer", "2"], "listSize": "1", "listName": ""}},
         ValueError, "For {} category, listName cannot be empty for item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist", "default": "{\"width\": \"12\"}", "items":
            "object", "properties": {"width": {"description": "", "default": "", "type": ""}}, "listName": ""}},
         ValueError, "For {} category, listName cannot be empty for item name {}".format(CAT_NAME, ITEM_NAME)),
        ({ITEM_NAME: {"description": "expression", "type": "kvlist",
                      "default": "{\"key\": \"1.0\", \"key\": \"val2\"}", "items": "float", "listName": 2}},
         TypeError, "For {} category, listName type must be a string for item name {}; got <class 'int'>".format(
            CAT_NAME, ITEM_NAME))
    ])
    async def test__validate_category_val_list_type_bad(self, config, exc_name, reason):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with pytest.raises(Exception) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=config,
                                               set_value_val_from_default_val=False)
        assert excinfo.type is exc_name
        assert reason == str(excinfo.value)

    @pytest.mark.parametrize("config", [
        {"include": {"description": "A list of variables to include", "type": "list", "items": "string",
                     "default": "[]"}},
        {"include": {"description": "A list of variables to include", "type": "list", "items": "string",
                     "default": "[\"first\", \"second\"]"}},
        {"include": {"description": "A list of variables to include", "type": "list", "items": "integer",
                     "default": "[\"1\", \"0\"]"}},
        {"include": {"description": "A list of variables to include", "type": "list", "items": "float",
                     "default": "[\"0.5\", \"123.57\"]"}},
        {"include": {"description": "A list of variables to include", "type": "list", "items": "float",
                     "default": "[\".5\", \"1.79e+308\"]", "listSize": "2"}},
        {"include": {"description": "A list of variables to include", "type": "list", "items": "string",
                     "default": "[\"var1\", \"var2\"]", "listSize": "2"}},
        {"include": {"description": "A list of variables to include", "type": "list", "items": "string",
                     "default": "[]", "listSize": "1"}},
        {"include": {"description": "A list of variables to include", "type": "list", "items": "integer",
                     "default": "[\"10\", \"100\", \"200\", \"300\"]", "listSize": "4"}},
        {"include": {"description": "A list of variables to include", "type": "list", "items": "object",
                     "default": "[{\"datapoint\": \"voltage\"}]",
                     "properties": {"datapoint": {"description": "The datapoint name to create", "displayName":
                         "Datapoint", "type": "string", "default": ""}}}},
        {"include": {"description": "A simple list", "type": "list", "default": "[\"integer\", \"float\"]",
                     "items": "enumeration", "options": ["integer", "float"]}},
        {"include": {"description": "A list of expressions and values", "type": "kvlist", "items": "string",
                    "default": "{}", "order": "1", "displayName": "labels"}},
        {"include": {"description": "A list of expressions and values", "type": "kvlist", "items": "string",
                     "default": "{\"key\": \"value\"}", "order": "1", "displayName": "labels"}},
        {"include": {"description": "A list of expressions and values", "type": "kvlist", "items": "integer",
                     "default": "{\"key\": \"13\"}", "order": "1", "displayName": "labels"}},
        {"include": {"description": "A list of expressions and values", "type": "kvlist", "items": "float",
                     "default": "{\"key\": \"13.13\"}", "order": "1", "displayName": "labels"}},
        {"include": {"description": "A list of expressions and values", "type": "kvlist", "items": "string",
                     "default": "{\"key\": \"value\"}", "order": "1", "displayName": "labels", "listSize": "1"}},
        {"include": {"description": "A list of expressions and values", "type": "kvlist", "items": "integer",
                     "default": "{\"key\": \"13\"}", "order": "1", "displayName": "labels", "listSize": "1"}},
        {"include": {"description": "A list of expressions and values", "type": "kvlist", "items": "float",
                     "default": "{\"key\": \"13.13\"}", "order": "1", "displayName": "labels", "listSize": "1"}},
        {"include": {"description": "A list of expressions and values", "type": "kvlist", "items": "float",
                     "default": "{}", "order": "1", "displayName": "labels", "listSize": "3"}},
        {"include": {"description": "A list of expressions and values", "type": "kvlist", "items": "object",
                     "default": "{\"register\": {\"width\": \"2\"}}", "order": "1", "displayName": "labels",
                     "properties": {"width": {"description": "Number of registers to read", "displayName": "Width",
                                              "type": "integer", "maximum": "4", "default": "1"}}}},
        {"include": {"description": "A list of expressions and values ", "type": "kvlist", "default":
            "{\"key1\": \"integer\", \"key2\": \"float\"}", "items": "enumeration", "options": ["integer", "float"]}}
    ])
    async def test__validate_category_val_list_type_good(self, config):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        res = await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=config,
                                                 set_value_val_from_default_val=True)
        assert config['include']['default'] == res['include']['default']
        assert config['include']['default'] == res['include']['value']

    @pytest.mark.parametrize("_type, value, from_default_val", [
        ("integer", " ", False),
        ("string", "", False),
        ("string", " ", False),
        ("JSON", "", False),
        ("JSON", " ", False),
        ("bucket", "", False),
        ("bucket", " ", False),
        ("list", "", False),
        ("list", " ", False),
        ("kvlist", "", False),
        ("kvlist", " ", False),
        ("integer", " ", True),
        ("string", "", True),
        ("string", " ", True),
        ("JSON", "", True),
        ("JSON", " ", True),
        ("bucket", "", True),
        ("bucket", " ", True),
        ("list", "", True),
        ("list", " ", True),
        ("kvlist", "", True),
        ("kvlist", " ", True)
    ])
    async def test__validate_category_val_with_optional_mandatory(self, _type, value, from_default_val):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config = {ITEM_NAME: {"description": "test description", "type": _type, "default": value,
                                   "mandatory": "true"}}
        if _type == "bucket":
            test_config[ITEM_NAME]['properties'] = {"key": "foo"}
        elif _type in ("list", "kvlist"):
            test_config[ITEM_NAME]['items'] = "string"

        with pytest.raises(Exception) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                               set_value_val_from_default_val=from_default_val)
        assert excinfo.type is ValueError
        assert ("For {} category, A default value must be given for {}"
                "").format(CAT_NAME, ITEM_NAME) == str(excinfo.value)

    async def test__validate_category_val_with_enum_type(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config = {
            ITEM_NAME: {
                "description": "test description val",
                "type": "enumeration",
                "default": "A",
                "options": ["A", "B", "C"]
            }
        }
        c_return_value = await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                                            set_value_val_from_default_val=True)
        assert isinstance(c_return_value, dict)
        assert 1 == len(c_return_value)
        test_item_val = c_return_value.get(ITEM_NAME)
        assert isinstance(test_item_val, dict)
        assert 5 == len(test_item_val)
        assert "test description val" == test_item_val.get("description")
        assert "enumeration" == test_item_val.get("type")
        assert "A" == test_item_val.get("default")
        assert "A" == test_item_val.get("value")

        # deep copy check to make sure test_config wasn't modified in the
        # method call
        assert test_config is not c_return_value
        assert isinstance(test_config, dict)
        assert 1 == len(test_config)
        test_item_val = test_config.get(ITEM_NAME)
        assert isinstance(test_item_val, dict)
        assert 4 == len(test_item_val)
        assert "test description val" == test_item_val.get("description")
        assert "enumeration" == test_item_val.get("type")
        assert "A" == test_item_val.get("default")

    @pytest.mark.parametrize("test_input, test_value, clean_value", [
        ("boolean", "false", "false"),
        ("integer", "123", "123"),
        ("string", "blah", "blah"),
        ("IPv4", "127.0.0.1", "127.0.0.1"),
        ("IPv6", "2001:db8::", "2001:db8::"),
        ("password", "not implemented", "not implemented"),
        ("X509 certificate", "not implemented", "not implemented"),
        ("JSON", "{\"foo\": \"bar\"}", '{"foo": "bar"}'),
        ("northTask", "north_task_category", "north_task_category")
    ])
    async def test__validate_category_val_valid_type(self, reset_singleton, test_input, test_value, clean_value):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config = {
            ITEM_NAME: {
                "description": "test description val",
                "type": test_input,
                "default": test_value,
            },
        }
        c_return_value = await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                                            set_value_val_from_default_val=True)
        assert c_return_value[ITEM_NAME]["type"] == test_input
        assert c_return_value[ITEM_NAME]["value"] == clean_value

    async def test__validate_category_val_invalid_type(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        item_name = 'test_item_name'
        test_config = {
            item_name: {
                "description": "test description val",
                "type": "blablabla",
                "default": "test default val",
            },
        }
        with pytest.raises(ValueError) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                               set_value_val_from_default_val=True)
        assert 'For {} category, invalid entry value for entry name "type" for item name {}. valid type strings ' \
               'are: {}'.format(CAT_NAME, item_name, _valid_type_strings) == str(excinfo.value)

    @pytest.mark.parametrize("test_input", ["type", "description", "default"])
    async def test__validate_category_val_missing_entry(self, reset_singleton, test_input):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config = {
            ITEM_NAME: {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
            },
        }
        del test_config['test_item_name'][test_input]
        with pytest.raises(ValueError) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                               set_value_val_from_default_val=True)
        assert 'For {} category, missing entry name {} for item name {}'.format(
            CAT_NAME, test_input, ITEM_NAME) == str(excinfo.value)

    async def test__validate_category_val_config_without_default_notuse_value_val(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config = {
            ITEM_NAME: {
                "description": "test description val",
                "type": "string",
            },
        }
        with pytest.raises(ValueError) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                               set_value_val_from_default_val=True)
        assert 'For {} category, missing entry name default for item name {}'.format(
            CAT_NAME, ITEM_NAME) == str(excinfo.value)

    async def test__validate_category_val_config_with_default_andvalue_val_notuse_value_val(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config = {
            ITEM_NAME: {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                "value": "test value val"
            },
        }
        with pytest.raises(ValueError) as excinfo:
            await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                               set_value_val_from_default_val=True)
        assert 'Specifying value_name and value_val for item_name test_item_name is not allowed if desired behavior is to use default_val as value_val' in str(
            excinfo.value)

    async def test__merge_category_vals_same_items_different_values(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config_new = {
            ITEM_NAME: {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                "value": "test value val"
            },
        }
        test_config_storage = {
            ITEM_NAME: {
                "description": "test description val storage",
                "type": "string",
                "default": "test default val storage",
                "value": "test value val storage"
            },
        }
        c_return_value = await c_mgr._merge_category_vals(test_config_new, test_config_storage,
                                                          keep_original_items=True, category_name=CAT_NAME)
        assert isinstance(c_return_value, dict)
        assert len(c_return_value) is 1
        test_item_val = c_return_value.get(ITEM_NAME)
        assert isinstance(test_item_val, dict)
        assert len(test_item_val) is 4
        assert test_item_val.get("description") is "test description val"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val"
        # use value val from storage
        assert test_item_val.get("value") is "test value val storage"
        # return new dictionary, do not modify parameters passed in
        assert test_config_new is not c_return_value
        assert test_config_storage is not c_return_value
        assert test_config_new is not test_config_storage

    async def test__merge_category_vals_deprecated(self, reset_singleton, mocker):
        async def async_mock(return_value):
            return return_value

        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock('CONCH')
        else:
            _rv = asyncio.ensure_future(async_mock('CONCH'))

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config_new = {
            "test_item_name1": {
                "description": "test description val storage1",
                "type": "string",
                "default": "test default val storage1",
                "value": "test value val storage1",
                "deprecated": "true"
            },
            "test_item_name2": {
                "description": "test description val2",
                "type": "string",
                "default": "test default val2",
                "value": "test value val2"
            },
        }
        test_config_storage = {
            "test_item_name1": {
                "description": "test description val storage1",
                "type": "string",
                "default": "test default val storage1",
                "value": "test value val storage1"
            },
            "test_item_name2": {
                "description": "test description val storage2",
                "type": "string",
                "default": "test default val storage2",
                "value": "test value val storage2"
            },
        }
        expected_new_value = {
            "test_item_name2": {
                "description": "test description val2",
                "type": "string",
                "default": "test default val2",
                "value": "test value val storage2"
            },
        }
        mocker.patch.object(AuditLogger, '__init__', return_value=None)
        mocker.patch.object(AuditLogger, 'information', return_value=_rv)
        c_return_value = await c_mgr._merge_category_vals(test_config_new, test_config_storage,
                                                          keep_original_items=True, category_name=CAT_NAME)
        assert expected_new_value == c_return_value

    async def test__merge_category_vals_no_mutual_items_ignore_original(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config_new = {
            ITEM_NAME: {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                "value": "test value val"
            },
        }
        test_config_storage = {
            "test_item_name_storage": {
                "description": "test description val storage",
                "type": "string",
                "default": "test default val storage",
                "value": "test value val storage"
            },
        }
        c_return_value = await c_mgr._merge_category_vals(test_config_new, test_config_storage,
                                                          keep_original_items=False, category_name=CAT_NAME)
        assert isinstance(c_return_value, dict)
        # ignore "test_item_name_storage" and include ITEM_NAME
        assert len(c_return_value) is 1
        test_item_val = c_return_value.get(ITEM_NAME)
        assert isinstance(test_item_val, dict)
        assert len(test_item_val) is 4
        assert test_item_val.get("description") is "test description val"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val"
        assert test_item_val.get("value") is "test value val"
        assert test_config_new is not c_return_value
        assert test_config_storage is not c_return_value
        assert test_config_new is not test_config_storage

    async def test__merge_category_vals_no_mutual_items_include_original(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        test_config_new = {
            ITEM_NAME: {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                "value": "test value val"
            },
        }
        test_config_storage = {
            "test_item_name_storage": {
                "description": "test description val storage",
                "type": "string",
                "default": "test default val storage",
                "value": "test value val storage"
            },
        }
        c_return_value = await c_mgr._merge_category_vals(test_config_new, test_config_storage,
                                                          keep_original_items=True, category_name=CAT_NAME)
        assert isinstance(c_return_value, dict)
        # include "test_item_name_storage" and ITEM_NAME
        assert len(c_return_value) is 2
        test_item_val = c_return_value.get(ITEM_NAME)
        assert isinstance(test_item_val, dict)
        assert len(test_item_val) is 4
        assert test_item_val.get("description") is "test description val"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val"
        assert test_item_val.get("value") is "test value val"
        test_item_val = c_return_value.get("test_item_name_storage")
        assert isinstance(test_item_val, dict)
        assert len(test_item_val) is 4
        assert test_item_val.get(
            "description") is "test description val storage"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val storage"
        assert test_item_val.get("value") is "test value val storage"
        assert test_config_new is not c_return_value
        assert test_config_storage is not c_return_value
        assert test_config_new is not test_config_storage

    p1 = {ITEM_NAME: {"description": "test description val", "type": "string", "default": "test default val",
                      "value": "test value val", "readonly": "true"}}
    p2 = {ITEM_NAME: {"description": "test description val", "type": "string", "default": "test default val",
                      "value": "test value val", "readonly": "false", "order": 3}}
    p3 = {ITEM_NAME: {"description": "test description val", "type": "string", "default": "test default val",
                      "value": "test value val", "readonly": "true", "order": 3, "length": 80}}
    p4 = {ITEM_NAME: {"description": "test description val", "type": "integer", "default": "1", "minimum": 0,
                      "maximum": 5}}
    p5 = {"test_item_name_storage": {"description": "", "type": "integer", "default": "10", "value": "100",
                                     "minimum": 10, "maximum": 100, "order": 1, "displayName": "test"}}
    p6 = {"test_item_name_storage": {"description": "", "type": "integer", 'default': "3", "value": "100",
                                     "rule": "value < 200", "order": 1}}

    @pytest.mark.parametrize("idx, new_config, keep_original_items", [
        (1, p1, False), (2, p2, False), (3, p3, False), (4, p4, False), (5, p5, False), (6, p6, False),
        (1, p1, True), (2, p2, True), (3, p3, True), (4, p4, True), (5, p5, True), (6, p6, True),
    ])
    async def test__merge_category_vals_with_optional_attributes(self, reset_singleton, idx, new_config,
                                                                 keep_original_items):
        def verify_data_ignore_original_items():
            assert len(actual_result) == 1
            actual = list(actual_result.values())[0]
            if idx == 1:
                assert ITEM_NAME in actual_result
                assert 'test_item_name_storage' not in actual_result
                assert len(actual) == 5
                assert actual['description'] == "test description val"
                assert actual['type'] == "string"
                assert actual['default'] == "test default val"
                assert actual['value'] == "test value val"
                assert actual["readonly"] == "true"
            elif idx == 2:
                assert ITEM_NAME in actual_result
                assert 'test_item_name_storage' not in actual_result
                assert len(actual) == 6
                assert actual['description'] == "test description val"
                assert actual['type'] == "string"
                assert actual['default'] == "test default val"
                assert actual['value'] == "test value val"
                assert actual["readonly"] == "false"
                assert actual['order'] == 3
            elif idx == 3:
                assert ITEM_NAME in actual_result
                assert 'test_item_name_storage' not in actual_result
                assert len(actual) == 7
                assert actual['description'] == "test description val"
                assert actual['type'] == "string"
                assert actual['default'] == "test default val"
                assert actual['value'] == "test value val"
                assert actual["readonly"] == "true"
                assert actual['order'] == 3
                assert actual['length'] == 80
            elif idx == 4:
                assert ITEM_NAME in actual_result
                assert 'test_item_name_storage' not in actual_result
                assert len(actual) == 6
                assert actual['description'] == "test description val"
                assert actual['type'] == "integer"
                assert actual['default'] == "1"
                assert actual['value'] == "1"
                assert actual['minimum'] == 0
                assert actual['maximum'] == 5
            elif idx == 5:
                assert ITEM_NAME not in actual_result
                assert 'test_item_name_storage' in actual_result
                assert len(actual) == 8
                assert actual['description'] == ""
                assert actual['type'] == "integer"
                assert actual['default'] == "10"
                assert actual['value'] == "100"
                assert actual["minimum"] == 10
                assert actual['maximum'] == 100
                assert actual['order'] == 1
                assert actual['displayName'] == "test"
            elif idx == 6:
                assert ITEM_NAME not in actual_result
                assert 'test_item_name_storage' in actual_result
                assert len(actual) == 6
                assert actual['description'] == ""
                assert actual['type'] == "integer"
                assert actual['default'] == "3"
                assert actual['value'] == "100"
                assert actual["order"] == 1
                assert actual['rule'] == "value < 200"

        def verify_data_include_original_items():
            assert len(actual_result) == 2
            item_name1 = ITEM_NAME
            item_name2 = 'test_item_name_storage'
            assert item_name1 in actual_result
            assert item_name2 in actual_result
            actual_item1 = actual_result[item_name1]
            actual_item2 = actual_result[item_name2]
            if idx == 1:
                assert len(actual_item1) == 5
                assert actual_item1['description'] == "test description val"
                assert actual_item1['type'] == "string"
                assert actual_item1['default'] == "test default val"
                assert actual_item1['value'] == "test value val"
                assert actual_item1["readonly"] == "true"
                assert len(actual_item2) == 7
                assert actual_item2['description'] == ""
                assert actual_item2['type'] == "integer"
                assert actual_item2['default'] == "10"
                assert actual_item2['value'] == "100"
                assert actual_item2["minimum"] == 20
                assert actual_item2["maximum"] == 200
                assert actual_item2["order"] == 1
            elif idx == 2:
                assert len(actual_item1) == 6
                assert actual_item1['description'] == "test description val"
                assert actual_item1['type'] == "string"
                assert actual_item1['default'] == "test default val"
                assert actual_item1['value'] == "test value val"
                assert actual_item1["readonly"] == "false"
                assert actual_item1["order"] == 3
                assert len(actual_item2) == 7
                assert actual_item2['description'] == ""
                assert actual_item2['type'] == "integer"
                assert actual_item2['default'] == "10"
                assert actual_item2['value'] == "100"
                assert actual_item2["minimum"] == 20
                assert actual_item2["maximum"] == 200
                assert actual_item2["order"] == 1
            elif idx == 3:
                assert len(actual_item1) == 7
                assert actual_item1['description'] == "test description val"
                assert actual_item1['type'] == "string"
                assert actual_item1['default'] == "test default val"
                assert actual_item1['value'] == "test value val"
                assert actual_item1["readonly"] == "true"
                assert actual_item1["order"] == 3
                assert actual_item1['length'] == 80
                assert len(actual_item2) == 7
                assert actual_item2['description'] == ""
                assert actual_item2['type'] == "integer"
                assert actual_item2['default'] == "10"
                assert actual_item2['value'] == "100"
                assert actual_item2["minimum"] == 20
                assert actual_item2["maximum"] == 200
                assert actual_item2["order"] == 1
            elif idx == 4:
                assert len(actual_item1) == 6
                assert actual_item1['description'] == "test description val"
                assert actual_item1['type'] == "integer"
                assert actual_item1['default'] == "1"
                assert actual_item1['value'] == "1"
                assert actual_item1["minimum"] == 0
                assert actual_item1['maximum'] == 5
                assert len(actual_item2) == 7
                assert actual_item2['description'] == ""
                assert actual_item2['type'] == "integer"
                assert actual_item2['default'] == "10"
                assert actual_item2['value'] == "100"
                assert actual_item2["minimum"] == 20
                assert actual_item2["maximum"] == 200
                assert actual_item2["order"] == 1
            elif idx == 5:
                assert len(actual_item1) == 6
                assert actual_item1['description'] == "test description val"
                assert actual_item1['type'] == "string"
                assert actual_item1['default'] == "test default val"
                assert actual_item1['value'] == "test value val"
                assert actual_item1["readonly"] == "false"
                assert actual_item1["order"] == 2
                assert len(actual_item2) == 8
                assert actual_item2['description'] == ""
                assert actual_item2['type'] == "integer"
                assert actual_item2['default'] == "10"
                assert actual_item2['value'] == "100"
                assert actual_item2["minimum"] == 10
                assert actual_item2["maximum"] == 100
                assert actual_item2["order"] == 1
                assert actual_item2["displayName"] == "test"
            elif idx == 6:
                assert len(actual_item1) == 6
                assert actual_item1['description'] == "test description val"
                assert actual_item1['type'] == "string"
                assert actual_item1['default'] == "test default val"
                assert actual_item1['value'] == "test value val"
                assert actual_item1["readonly"] == "false"
                assert actual_item1["order"] == 2
                assert len(actual_item2) == 6
                assert actual_item2['description'] == ""
                assert actual_item2['type'] == "integer"
                assert actual_item2['default'] == "3"
                assert actual_item2['value'] == "100"
                assert actual_item2["order"] == 1
                assert actual_item2["rule"] == "value < 200"

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        storage_config = {
            "test_item_name_storage": {
                "description": "",
                "type": "integer",
                "default": "10",
                "value": "100",
                "minimum": 20,
                "maximum": 200,
                "order": 1
            },
            ITEM_NAME: {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                "value": "test value val",
                "readonly": "false",
                "order": 2
            }
        }
        actual_result = await c_mgr._merge_category_vals(
            new_config, storage_config, keep_original_items=keep_original_items, category_name=CAT_NAME)
        assert isinstance(actual_result, dict)
        if keep_original_items:
            getattr(verify_data_include_original_items, "__call__")()
        else:
            getattr(verify_data_ignore_original_items, "__call__")()

    @pytest.mark.parametrize("payload, message", [
        ((2, 'catvalue', 'catdesc'), "category_name must be a string"),
        (('catname', 'catvalue', 3), "category_description must be a string")
    ])
    async def test_bad_create_category(self, reset_singleton, payload, message):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with pytest.raises(Exception) as excinfo:
            await c_mgr.create_category(category_name=payload[0], category_value=payload[1],
                                        category_description=payload[2])
        assert excinfo.type is TypeError
        assert message == str(excinfo.value)

    @pytest.mark.parametrize("rule", [
        'value * 3 == 6',
        'value > 4',
        'value % 2 == 0',
        'value * (value + 1) == 9',
        '(value + 1) / (value - 1) >= 3',
        'sqrt(value) < 1',
        'pow(value, value) != 27',
        'value ^ value == 2',
        'factorial(value) != 6',
        'fabs(value) != 3.0',
        'ceil(value) != 3',
        'floor(value) != 3',
        'sin(value) <= 0',
        'degrees(value) < 171'
    ])
    async def test_bad_rule_create_category(self, reset_singleton, rule):

        async def async_mock(return_value):
            return return_value

        d = {'info': {'rule': rule, 'default': '3', 'type': 'integer', 'description': 'Test', 'value': '3'}}
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _se = await async_mock(d)
        else:
            _se = asyncio.ensure_future(async_mock(d))
        
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_validate_category_val', side_effect=[_se,
                                                                                           Exception()]) as valpatch:
                with pytest.raises(Exception) as excinfo:
                    await c_mgr.create_category('catname', 'catvalue', 'catdesc')
                assert excinfo.type is ValueError
                assert 'For catname category, The value of info is not valid, please supply a valid value' == str(excinfo.value)
            valpatch.assert_called_once_with('catname', 'catvalue', True)
        assert 1 == log_exc.call_count

    async def test_create_category_good_newval_bad_storageval_good_update(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock({})
            _se = await async_mock({})
            _sr = await async_mock((False, None, None, None))
        else:
            _rv = asyncio.ensure_future(async_mock({}))
            _se = asyncio.ensure_future(async_mock({}))
            _sr = asyncio.ensure_future(async_mock((False, None, None, None)))
        
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_validate_category_val', side_effect=[_se, Exception()]) as valpatch:
                with patch.object(ConfigurationManager, '_read_category_val', return_value=_rv) as readpatch:
                    with patch.object(ConfigurationManager, '_merge_category_vals') as mergepatch:
                        with patch.object(ConfigurationManager, '_run_callbacks', return_value=_rv) as callbackpatch:
                            with patch.object(ConfigurationManager, 'search_for_ACL_recursive_from_cat_name',
                                              return_value=_sr) as searchaclpatch:
                                cat = await c_mgr.create_category('catname', 'catvalue', 'catdesc')
                                assert cat is None
                            searchaclpatch.assert_called_once_with('catname')
                        callbackpatch.assert_called_once_with('catname')
                    mergepatch.assert_not_called()
                readpatch.assert_called_once_with('catname')
            valpatch.assert_has_calls([call('catname', 'catvalue', True), call('catname', {}, False)])
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('category_value for category_name %s from storage is corrupted; using category_value without merge', 'catname')

    async def test_create_category_good_newval_bad_storageval_bad_update(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock({})
            _se = await async_mock({})
            _sr = await async_mock((False, None, None, None))
        else:
            _rv = asyncio.ensure_future(async_mock({}))
            _se = asyncio.ensure_future(async_mock({}))
            _sr = asyncio.ensure_future(async_mock((False, None, None, None)))
                
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_validate_category_val', side_effect=[_se, Exception]) as valpatch:
                with patch.object(ConfigurationManager, '_read_category_val', return_value=_rv) as readpatch:
                    with patch.object(ConfigurationManager, '_merge_category_vals') as mergepatch:
                        with patch.object(ConfigurationManager, '_run_callbacks', return_value=_rv) as callbackpatch:
                            with patch.object(ConfigurationManager, 'search_for_ACL_recursive_from_cat_name',
                                              return_value=_sr) as searchaclpatch:
                                await c_mgr.create_category('catname', 'catvalue', 'catdesc')
                            searchaclpatch.assert_called_once_with('catname')
                        callbackpatch.assert_called_once_with('catname')
                    mergepatch.assert_not_called()
                readpatch.assert_called_once_with('catname')
            valpatch.assert_has_calls([call('catname', 'catvalue', True), call('catname', {}, False)])
        assert 1 == log_exc.call_count
        calls = [call('category_value for category_name %s from storage is corrupted; using category_value without merge', 'catname'),
                 call('Unable to create new category based on category_name %s and category_description %s and category_json_schema %s', 'catname', 'catdesc')]
        assert log_exc.has_calls(calls, any_order=True)

    # (merged_value)
    async def test_create_category_good_newval_good_storageval_nochange(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        all_cat_names = [('rest_api', 'Fledge Admin and User REST API', 'rest_api'), ('catname', 'catdesc', 'catname')]
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock({})
            _rv2 = await async_mock(all_cat_names)
            _se = await async_mock({})
        else:
            _rv1 = asyncio.ensure_future(async_mock({}))
            _rv2 = asyncio.ensure_future(async_mock(all_cat_names))
            _se = asyncio.ensure_future(async_mock({}))

        with patch.object(ConfigurationManager, '_validate_category_val', side_effect=[_se, _se]) as valpatch:
            with patch.object(ConfigurationManager, '_read_category_val', return_value=_rv1) as readpatch:
                with patch.object(ConfigurationManager, '_read_all_category_names', return_value=_rv2) as read_all_patch:
                    with patch.object(ConfigurationManager, '_merge_category_vals', return_value=_rv1) as mergepatch:
                        with patch.object(ConfigurationManager, '_run_callbacks') as callbackpatch:
                            with patch.object(ConfigurationManager, '_update_category') as updatepatch:
                                cat = await c_mgr.create_category('catname', 'catvalue', 'catdesc')
                                assert cat is None
                            updatepatch.assert_not_called()
                        callbackpatch.assert_not_called()
                    mergepatch.assert_called_once_with({}, {}, False, 'catname')
                read_all_patch.assert_called_once_with()
            readpatch.assert_called_once_with('catname')
        valpatch.assert_has_calls([call('catname', 'catvalue', True), call('catname', {}, False)])

    async def test_create_category_good_newval_good_storageval_good_update(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        all_cat_names = [('rest_api', 'Fledge Admin and User REST API', 'rest_api'), ('catname', 'catdesc', 'catname')]
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock({})
            _rv2 = await async_mock(all_cat_names)
            _rv3 = await async_mock({'bla': 'bla'})
            _rv4 = await async_mock(None)
            _se = await async_mock({})
            _sr = await async_mock((False, None, None, None))
        else:
            _rv1 = asyncio.ensure_future(async_mock({}))
            _rv2 = asyncio.ensure_future(async_mock(all_cat_names))
            _rv3 = asyncio.ensure_future(async_mock({'bla': 'bla'}))
            _rv4 = asyncio.ensure_future(async_mock(None))
            _se = asyncio.ensure_future(async_mock({}))
            _sr = asyncio.ensure_future(async_mock((False, None, None, None)))

        with patch.object(ConfigurationManager, '_validate_category_val', side_effect=[_se, _se]) as valpatch:
            with patch.object(ConfigurationManager, '_read_category_val', return_value=_rv1) as readpatch:
                with patch.object(ConfigurationManager, '_read_all_category_names',
                                  return_value=_rv2) as read_all_patch:
                    with patch.object(ConfigurationManager, '_merge_category_vals', return_value=_rv3) as mergepatch:
                        with patch.object(ConfigurationManager, '_run_callbacks', return_value=_rv4) as callbackpatch:
                            with patch.object(ConfigurationManager, '_update_category',
                                              return_value=_rv4) as updatepatch:
                                with patch.object(AuditLogger, '__init__', return_value=None):
                                    with patch.object(AuditLogger, 'information', return_value=_rv4) as auditinfopatch:
                                        with patch.object(ConfigurationManager,
                                                          'search_for_ACL_recursive_from_cat_name',
                                                          return_value=_sr) as searchaclpatch:
                                            cat = await c_mgr.create_category('catname', 'catvalue', 'catdesc')
                                            assert cat is None
                                        searchaclpatch.assert_called_once_with('catname')
                                    auditinfopatch.assert_called_once_with(
                                        'CONCH', {'category': 'catname', 'item': 'configurationChange', 'oldValue': {},
                                                  'newValue': {'bla': 'bla'}})
                            updatepatch.assert_called_once_with('catname', {'bla': 'bla'}, 'catdesc', 'catname')
                        callbackpatch.assert_called_once_with('catname')
                    mergepatch.assert_called_once_with({}, {}, False, 'catname')
                read_all_patch.assert_called_once_with()
            readpatch.assert_called_once_with('catname')
        valpatch.assert_has_calls([call('catname', 'catvalue', True), call('catname', {}, False)])

    async def test_create_category_good_newval_good_storageval_bad_update(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        all_cat_names = [('rest_api', 'Fledge Admin and User REST API', 'rest_api'), ('catname', 'catdesc', 'catname')]
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock({})
            _rv2 = await async_mock(all_cat_names)
            _rv4 = await async_mock(None)
            _se = await async_mock({})
        else:
            _rv1 = asyncio.ensure_future(async_mock({}))
            _rv2 = asyncio.ensure_future(async_mock(all_cat_names))
            _rv4 = asyncio.ensure_future(async_mock(None))
            _se = asyncio.ensure_future(async_mock({}))
        
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_validate_category_val', side_effect=[_se, _se]) as valpatch:
                with patch.object(ConfigurationManager, '_read_category_val', return_value=_rv1) as readpatch:
                    with patch.object(ConfigurationManager, '_read_all_category_names', return_value=_rv2) as read_all_patch:
                        with patch.object(ConfigurationManager, '_merge_category_vals', side_effect=TypeError) as mergepatch:
                            with patch.object(ConfigurationManager, '_run_callbacks') as callbackpatch:
                                with pytest.raises(Exception) as excinfo:
                                    await c_mgr.create_category('catname', 'catvalue', 'catdesc')
                                assert excinfo.type is TypeError
                            callbackpatch.assert_not_called()
                        mergepatch.assert_called_once_with({}, {}, False, 'catname')
                    read_all_patch.assert_called_once_with()
                readpatch.assert_called_once_with('catname')
            valpatch.assert_has_calls([call('catname', 'catvalue', True), call('catname', {}, False)])
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('Unable to create new category based on category_name %s and category_description %s '
                                        'and category_json_schema %s', 'catname', 'catdesc', {})

    async def test_create_category_good_newval_no_storageval_good_create(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock({})
            _rv2 = await async_mock(None)
            _sr = await async_mock((False, None, None, None))
        else:
            _rv1 = asyncio.ensure_future(async_mock({}))
            _rv2 = asyncio.ensure_future(async_mock(None))
            _sr = asyncio.ensure_future(async_mock((False, None, None, None)))

        with patch.object(ConfigurationManager, '_validate_category_val', return_value=_rv1) as valpatch:
            with patch.object(ConfigurationManager, '_read_category_val', return_value=_rv2) as readpatch:
                with patch.object(ConfigurationManager, '_create_new_category', return_value=_rv2) as createpatch:
                    with patch.object(ConfigurationManager, '_run_callbacks', return_value=_rv2) as callbackpatch:
                        with patch.object(ConfigurationManager, 'search_for_ACL_recursive_from_cat_name',
                                          return_value=_sr) as searchaclpatch:
                            await c_mgr.create_category('catname', 'catvalue', "catdesc")
                        searchaclpatch.assert_called_once_with('catname')
                    callbackpatch.assert_called_once_with('catname')
                createpatch.assert_called_once_with('catname', {}, 'catdesc', None)
            readpatch.assert_called_once_with('catname')
        valpatch.assert_called_once_with('catname', 'catvalue', True)

    async def test_create_category_good_newval_no_storageval_bad_create(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock({})
            _rv2 = await async_mock(None)
        else:
            _rv1 = asyncio.ensure_future(async_mock({}))
            _rv2 = asyncio.ensure_future(async_mock(None))
        
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_validate_category_val', return_value=_rv1) as valpatch:
                with patch.object(ConfigurationManager, '_read_category_val', return_value=_rv2) as readpatch:
                    with patch.object(ConfigurationManager, '_create_new_category', side_effect=StorageServerError(None, None, None)) as createpatch:
                        with patch.object(ConfigurationManager, '_run_callbacks') as callbackpatch:
                            with pytest.raises(StorageServerError):
                                await c_mgr.create_category('catname', 'catvalue', "catdesc")
                        callbackpatch.assert_not_called()
                    createpatch.assert_called_once_with('catname', {}, 'catdesc', None)
                readpatch.assert_called_once_with('catname')
            valpatch.assert_called_once_with('catname', 'catvalue', True)
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('Unable to create new category based on category_name %s and category_description %s and category_json_schema %s', 'catname', 'catdesc', {})

    async def test_create_category_good_newval_keyerror_bad_create(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock({})
            _rv2 = await async_mock(None)
        else:
            _rv1 = asyncio.ensure_future(async_mock({}))
            _rv2 = asyncio.ensure_future(async_mock(None))
        
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_validate_category_val', return_value=_rv1) as valpatch:
                with patch.object(ConfigurationManager, '_read_category_val', return_value=_rv2) as readpatch:
                    with patch.object(ConfigurationManager, '_create_new_category', side_effect=KeyError()) as createpatch:
                        with patch.object(ConfigurationManager, '_run_callbacks') as callbackpatch:
                            with pytest.raises(KeyError):
                                await c_mgr.create_category('catname', 'catvalue', "catdesc")
                        callbackpatch.assert_not_called()
                    createpatch.assert_called_once_with('catname', {}, 'catdesc', None)
                readpatch.assert_called_once_with('catname')
            valpatch.assert_called_once_with('catname', 'catvalue', True)
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('Unable to create new category based on category_name %s and category_description %s and category_json_schema %s', 'catname', 'catdesc', {})

    async def test_create_category_bad_newval(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_validate_category_val', side_effect=Exception()) as valpatch:
                with patch.object(ConfigurationManager, '_read_category_val') as readpatch:
                    with patch.object(ConfigurationManager, '_create_new_category') as createpatch:
                        with patch.object(ConfigurationManager, '_run_callbacks') as callbackpatch:
                            with pytest.raises(Exception):
                                await c_mgr.create_category('catname', 'catvalue', "catdesc")
                        callbackpatch.assert_not_called()
                    createpatch.assert_not_called()
                readpatch.assert_not_called()
            valpatch.assert_called_once_with('catname', 'catvalue', True)
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('Unable to create new category based on category_name %s and category_description %s and category_json_schema %s', 'catname', 'catdesc', '')

    async def test_set_category_item_value_entry_good_update(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        category_name = 'catname'
        item_name = 'itemname'
        new_value_entry = 'newvalentry'
        storage_value_entry = {'value': 'test', 'description': 'Test desc', 'type': 'string', 'default': 'test'}
        c_mgr._cacheManager.update(category_name, "desc", {item_name: storage_value_entry})

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock(storage_value_entry)
            _rv2 = await async_mock(None)
        else:
            _rv1 = asyncio.ensure_future(async_mock(storage_value_entry))
            _rv2 = asyncio.ensure_future(async_mock(None))

        with patch.object(ConfigurationManager, '_read_item_val', return_value=_rv1) as readpatch:
            with patch.object(ConfigurationManager, '_update_value_val', return_value=_rv2) as updatepatch:
                with patch.object(ConfigurationManager, '_run_callbacks', return_value=_rv2) as callbackpatch:
                    await c_mgr.set_category_item_value_entry(category_name, item_name, new_value_entry)
                callbackpatch.assert_called_once_with(category_name)
            updatepatch.assert_called_once_with(category_name, item_name, new_value_entry)
        readpatch.assert_called_once_with(category_name, item_name)

    @pytest.mark.parametrize("new_value_entry, storage_result, exc_name, exc_msg", [
        ('', {'value': 'test', 'description': 'Test desc', 'type': 'string', 'default': 'test',
              'mandatory': 'true'}, ValueError, "A value must be given for itemname"),
        ('', {'value': '{}', 'description': 'Test desc', 'type': 'JSON', 'default': '{}',
              'mandatory': 'true'}, TypeError, "Unrecognized value name for item_name itemname"),
        ({}, {'value': '{}', 'description': 'Test desc', 'type': 'JSON', 'default': '{}',
              'mandatory': 'true'}, ValueError, "Dict cannot be set as empty. A value must be given for itemname"),
        (1, {'value': '{}', 'description': 'Test desc', 'type': 'JSON', 'default': '{}',
             'mandatory': 'true'}, TypeError, "Unrecognized value name for item_name itemname"),
        (' ', {'value': 'test1', 'description': 'Test desc', 'type': 'string', 'default': 'test1',
               'mandatory': 'true'}, ValueError, "A value must be given for itemname"),
        ('5', {'rule': 'value*3==9', 'default': '3', 'description': 'Test', 'value': '3',
               'type': 'integer'}, ValueError, "The value of itemname is not valid, please supply a valid value"),
        ('blah', {'value': 'woo', 'default': 'woo', 'description': 'enum types', 'type': 'enumeration',
                  'options': ['foo', 'woo']}, ValueError, "new value does not exist in options enum"),
        ('', {'value': 'woo', 'default': 'woo', 'description': 'enum types', 'type': 'enumeration',
              'options': ['foo', 'woo']}, ValueError, "entry_val cannot be empty"),
    ])
    async def test_set_category_item_value_entry_bad_update(self, reset_singleton, new_value_entry, storage_result,
                                                            exc_name, exc_msg):
        async def async_mock():
            return storage_result

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        category_name = 'catname'
        item_name = 'itemname'
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock()
        else:
            _rv = asyncio.ensure_future(async_mock())
        
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_read_item_val', return_value=_rv) as readpatch:
                with patch.object(ConfigurationManager, '_run_callbacks') as callbackpatch:
                    with pytest.raises(Exception) as excinfo:
                        await c_mgr.set_category_item_value_entry(category_name, item_name, new_value_entry)
                    assert excinfo.type is exc_name
                    assert exc_msg == str(excinfo.value)
                callbackpatch.assert_not_called()
            readpatch.assert_called_once_with(category_name, item_name)
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('Unable to set item value entry based on category_name %s and item_name %s and value_item_entry %s', category_name, item_name, new_value_entry)

    async def test_set_category_item_value_entry_bad_storage(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        category_name = 'catname'
        item_name = 'itemname'
        new_value_entry = 'newvalentry'
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(None)
        else:
            _rv = asyncio.ensure_future(async_mock(None))
        
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_read_item_val', return_value=_rv) as readpatch:
                with patch.object(ConfigurationManager, '_update_value_val') as updatepatch:
                    with patch.object(ConfigurationManager, '_run_callbacks') as callbackpatch:
                        with pytest.raises(ValueError) as excinfo:
                            await c_mgr.set_category_item_value_entry(category_name, item_name, new_value_entry)
                        assert 'No detail found for the category_name: {} and item_name: {}'.format(category_name, item_name) in str(excinfo.value)
                    callbackpatch.assert_not_called()
                updatepatch.assert_not_called()
            readpatch.assert_called_once_with(category_name, item_name)
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('Unable to set item value entry based on category_name %s and item_name %s and value_item_entry %s', 'catname', 'itemname', 'newvalentry')

    async def test_set_category_item_value_entry_no_change(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        category_name = 'catname'
        item_name = 'itemname'
        new_value_entry = 'newvalentry'

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(new_value_entry)
        else:
            _rv = asyncio.ensure_future(async_mock(new_value_entry))

        with patch.object(ConfigurationManager, '_read_item_val', return_value=_rv) as readpatch:
            with patch.object(ConfigurationManager, '_update_value_val') as updatepatch:
                with patch.object(ConfigurationManager, '_run_callbacks') as callbackpatch:
                    await c_mgr.set_category_item_value_entry(category_name, item_name, new_value_entry)
                callbackpatch.assert_not_called()
            updatepatch.assert_not_called()
        readpatch.assert_called_once_with(category_name, item_name)

    async def test_set_category_item_invalid_type_value(self, reset_singleton):
        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        category_name = 'catname'
        item_name = 'itemname'
        new_value_entry = 'newvalentry'
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock({'value': 'test', 'description': 'Test desc', 'type': 'boolean', 'default': 'test'})
        else:
            _rv = asyncio.ensure_future(async_mock({'value': 'test', 'description': 'Test desc', 'type': 'boolean', 'default': 'test'}))
        
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_read_item_val', return_value=_rv) as readpatch:
                with pytest.raises(Exception) as excinfo:
                    await c_mgr.set_category_item_value_entry(category_name, item_name, new_value_entry)
                assert excinfo.type is TypeError
                assert 'Unrecognized value name for item_name itemname' == str(excinfo.value)
            readpatch.assert_called_once_with(category_name, item_name)
        assert 1 == log_exc.call_count

    async def test_set_category_item_value_entry_with_enum_type(self, reset_singleton):
        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        category_name = 'catname'
        item_name = 'itemname'
        new_value_entry = 'foo'
        storage_value_entry = {"value": "woo", "default": "woo", "description": "enum types", "type": "enumeration", "options": ["foo", "woo"]}
        c_mgr._cacheManager.update(category_name, "desc", {item_name: storage_value_entry})

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock(storage_value_entry)
            _rv2 = await async_mock(None)
        else:
            _rv1 = asyncio.ensure_future(async_mock(storage_value_entry))
            _rv2 = asyncio.ensure_future(async_mock(None))

        with patch.object(ConfigurationManager, '_read_item_val', return_value=_rv1) as readpatch:
            with patch.object(ConfigurationManager, '_update_value_val', return_value=_rv2) as updatepatch:
                with patch.object(ConfigurationManager, '_run_callbacks', return_value=_rv2) as callbackpatch:
                    await c_mgr.set_category_item_value_entry(category_name, item_name, new_value_entry)
                callbackpatch.assert_called_once_with(category_name)
            updatepatch.assert_called_once_with(category_name, item_name, new_value_entry)
        readpatch.assert_called_once_with(category_name, item_name)

    @pytest.mark.parametrize("new_value_entry, message", [
        ("", "entry_val cannot be empty"),
        ("blah", "new value does not exist in options enum")
    ])
    async def test_set_category_item_value_entry_with_enum_type_exceptions(self, new_value_entry, message):
        async def async_mock():
            return {"default": "woo", "description": "enum types", "type": "enumeration",
                    "options": ["foo", "woo"]}

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        category_name = 'catname'
        item_name = 'itemname'

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock()
        else:
            _rv = asyncio.ensure_future(async_mock())
        
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_read_item_val', return_value=_rv) as readpatch:
                with pytest.raises(Exception) as excinfo:
                    await c_mgr.set_category_item_value_entry(category_name, item_name, new_value_entry)
                assert excinfo.type is ValueError
                assert message == str(excinfo.value)
            readpatch.assert_called_once_with(category_name, item_name)
        assert 1 == log_exc.call_count

    async def test_set_category_item_value_entry_with_rule_optional_attribute(self):

        async def async_mock():
            return {'rule': 'value*3==9', 'default': '3', 'description': 'Test', 'value': '3', 'type': 'integer'}

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        category_name = 'catname'
        item_name = 'info'
        new_value_entry = '13'
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock()
        else:
            _rv = asyncio.ensure_future(async_mock())
        
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_read_item_val', return_value=_rv) as readpatch:
                with pytest.raises(Exception) as excinfo:
                    await c_mgr.set_category_item_value_entry(category_name, item_name, new_value_entry)
                assert excinfo.type is ValueError
                assert 'The value of {} is not valid, please supply a valid value'.format(item_name) == str(excinfo.value)
            readpatch.assert_called_once_with(category_name, item_name)
        assert 1 == log_exc.call_count

    async def test_get_all_category_names_good(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock('bla')
        else:
            _rv = asyncio.ensure_future(async_mock('bla'))

        with patch.object(ConfigurationManager, '_read_all_category_names', return_value=_rv) as readpatch:
            ret_val = await c_mgr.get_all_category_names()
            assert 'bla' == ret_val
        readpatch.assert_called_once_with()

    @pytest.mark.parametrize("value", [
        "True", "False"
    ])
    async def test_get_all_category_names_with_root(self, reset_singleton, value):

        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock('bla')
        else:
            _rv = asyncio.ensure_future(async_mock('bla'))

        with patch.object(ConfigurationManager, '_read_all_groups', return_value=_rv) as readpatch:
            ret_val = await c_mgr.get_all_category_names(root=value)
            assert 'bla' == ret_val
        readpatch.assert_called_once_with(value, False)

    async def test_get_all_category_names_bad(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_read_all_category_names', side_effect=Exception()) as readpatch:
                with pytest.raises(Exception):
                    await c_mgr.get_all_category_names()
            readpatch.assert_called_once_with()
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('Unable to read all category names')

    async def test_get_category_all_items_good(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        category_name = 'catname'
        cat_value = {"config_item": {"type": "string", "default": "blah", "description": "Des", "value": "blah"}}
        cat_info = {'display_name': category_name, 'key': category_name, 'description': 'Test Des', "value": cat_value}
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(cat_info)
        else:
            _rv = asyncio.ensure_future(async_mock(cat_info))

        with patch.object(ConfigurationManager, '_read_category', return_value=_rv) as readpatch:
            ret_val = await c_mgr.get_category_all_items(category_name)
            assert cat_value == ret_val
        readpatch.assert_called_once_with(category_name)

    async def test_get_category_all_items_bad(self, reset_singleton):
        category_name = 'catname'
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_read_category', side_effect=Exception()) as readpatch:
                with pytest.raises(Exception):
                    await c_mgr.get_category_all_items(category_name)
            readpatch.assert_called_once_with(category_name)
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('Unable to get all category items of {} category.'.format(category_name))

    async def test_get_category_item_good(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        category_name = 'catname'
        item_name = 'item_name'
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock('bla')
            _rv2 = await async_mock(None)
        else:
            _rv1 = asyncio.ensure_future(async_mock('bla'))
            _rv2 = asyncio.ensure_future(async_mock(None))        

        with patch.object(ConfigurationManager, '_read_item_val', return_value=_rv1) as read_item_patch:
            with patch.object(ConfigurationManager, '_read_category', return_value=_rv2) as read_cat_patch:
                ret_val = await c_mgr.get_category_item(category_name, item_name)
                assert 'bla' == ret_val
            read_cat_patch.assert_called_once_with(category_name)
        read_item_patch.assert_called_once_with(category_name, item_name)

    async def test_get_category_item_bad(self, reset_singleton):
        category_name = 'catname'
        item_name = 'item_name'
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_read_item_val', side_effect=Exception()) as readpatch:
                with pytest.raises(Exception):
                    await c_mgr.get_category_item(category_name, item_name)
            readpatch.assert_called_once_with(category_name, item_name)
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('Unable to get category item based on category_name %s and item_name %s', 'catname', 'item_name')

    async def test_get_category_item_value_entry_good(self, reset_singleton):

        async def async_mock(return_value):
            return return_value

        category_name = 'catname'
        item_name = 'item_name'
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock('bla')
        else:
            _rv = asyncio.ensure_future(async_mock('bla'))        

        with patch.object(ConfigurationManager, '_read_value_val', return_value=_rv) as readpatch:
            ret_val = await c_mgr.get_category_item_value_entry(category_name, item_name)
            assert 'bla' == ret_val
        readpatch.assert_called_once_with(category_name, item_name)

    async def test_get_category_item_value_entry_bad(self, reset_singleton):
        category_name = 'catname'
        item_name = 'item_name'
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(_logger, 'exception') as log_exc:
            with patch.object(ConfigurationManager, '_read_value_val', side_effect=Exception()) as readpatch:
                with pytest.raises(Exception):
                    await c_mgr.get_category_item_value_entry(category_name, item_name)
            readpatch.assert_called_once_with(category_name, item_name)
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('Unable to get the "value" entry based on category_name %s and item_name %s', 'catname', 'item_name')

    async def test__create_new_category_good(self, reset_singleton):
        async def mock_coro():
            return {'response': [{'display_name': 'catname', 'category_name': 'catname', 'category_val': 'catval', 'description': 'catdesc'}]}

        async def async_mock(return_value):
            return return_value

        category_name = 'catname'
        category_val = 'catval'
        category_description = 'catdesc'


        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(None)
            _attr = await mock_coro()
        else:
            _rv = asyncio.ensure_future(async_mock(None))
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"insert_into_tbl.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)      

        with patch.object(AuditLogger, '__init__', return_value=None):
            with patch.object(AuditLogger, 'information', return_value=_rv) as auditinfopatch:
                with patch.object(PayloadBuilder, '__init__', return_value=None):
                    with patch.object(PayloadBuilder, 'INSERT', return_value=PayloadBuilder) as pbinsertpatch:
                        with patch.object(PayloadBuilder, 'payload', return_value=None) as pbpayloadpatch:
                            await c_mgr._create_new_category(category_name, category_val, category_description)
                        pbpayloadpatch.assert_called_once_with()
                    pbinsertpatch.assert_called_once_with(display_name=category_name, description=category_description,
                                                          key=category_name, value=category_val)
            auditinfopatch.assert_called_once_with('CONAD', {'category': category_val, 'name': category_name})
        storage_client_mock.insert_into_tbl.assert_called_once_with(
            'configuration', None)

    async def test_create_new_category_deprecated(self, reset_singleton):
        async def mock_coro():
            return {'response': [{
                'category_name': 'catname',
                'category_val': 'catval',
                'description': 'catdesc'
            }]
            }

        async def async_mock(return_value):
            return return_value

        category_name = 'catname'
        category_val = {
            "test_item_name1": {
                "description": "test description val1",
                "type": "string",
                "default": "test default val1",
                "deprecated": "true"
            },
            "test_item_name2": {
                "description": "test description val2",
                "type": "string",
                "default": "test default val2"
            },

        }
        category_val_actual = {
            "test_item_name2": {
                "description": "test description val2",
                "type": "string",
                "default": "test default val2"
            },
        }

        category_description = 'catdesc'

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(None)
            _attr = await mock_coro()
        else:
            _rv = asyncio.ensure_future(async_mock(None))
            _attr = asyncio.ensure_future(mock_coro())        

        attrs = {"insert_into_tbl.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(AuditLogger, '__init__', return_value=None):
            with patch.object(AuditLogger, 'information', return_value=_rv) as auditinfopatch:
                with patch.object(PayloadBuilder, '__init__', return_value=None):
                    with patch.object(PayloadBuilder, 'INSERT', return_value=PayloadBuilder) as pbinsertpatch:
                        with patch.object(PayloadBuilder, 'payload', return_value=None) as pbpayloadpatch:
                            await c_mgr._create_new_category(category_name, category_val, category_description)
                        pbpayloadpatch.assert_called_once_with()
                    pbinsertpatch.assert_called_once_with(display_name=category_name, description=category_description,
                                                          key=category_name, value=category_val_actual)
            auditinfopatch.assert_called_once_with('CONAD', {'category': category_val_actual, 'name': category_name})
        storage_client_mock.insert_into_tbl.assert_called_once_with('configuration', None)

    async def test__read_all_category_names_1_row(self, reset_singleton):
        async def mock_coro():
            return {'rows': [{'key': 'key1', 'description': 'description1', 'display_name': 'display key'}]}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"query_tbl_with_payload.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)

        c_mgr = ConfigurationManager(storage_client_mock)
        ret_val = await c_mgr._read_all_category_names()
        args, kwargs = storage_client_mock.query_tbl_with_payload.call_args
        assert 'configuration' == args[0]
        p = json.loads(args[1])
        assert {"return": ["key", "description", "value", "display_name", {"column": "ts", "alias": "timestamp", "format": "YYYY-MM-DD HH24:MI:SS.MS"}]} == p
        assert [('key1', 'description1', 'display key')] == ret_val

    async def test__read_all_category_names_2_row(self, reset_singleton):
        async def mock_coro():
            return {'rows': [{'key': 'key1', 'description': 'description1', 'display_name': 'display key1'}, {'key': 'key2', 'description': 'description2', 'display_name': 'display key2'}]}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"query_tbl_with_payload.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)
        ret_val = await c_mgr._read_all_category_names()
        args, kwargs = storage_client_mock.query_tbl_with_payload.call_args
        assert 'configuration' == args[0]
        p = json.loads(args[1])
        assert {"return": ["key", "description", "value", "display_name", {"column": "ts", "alias": "timestamp", "format": "YYYY-MM-DD HH24:MI:SS.MS"}]} == p
        assert [('key1', 'description1', 'display key1'), ('key2', 'description2', 'display key2')] == ret_val

    async def test__read_all_category_names_0_row(self, reset_singleton):
        async def mock_coro():
            return {'rows': []}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"query_tbl_with_payload.return_value": _attr }
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)
        ret_val = await c_mgr._read_all_category_names()
        args, kwargs = storage_client_mock.query_tbl_with_payload.call_args
        assert 'configuration' == args[0]
        p = json.loads(args[1])
        assert {"return": ["key", "description", "value", "display_name", {"column": "ts", "alias": "timestamp", "format": "YYYY-MM-DD HH24:MI:SS.MS"}]} == p
        assert [] == ret_val

    async def test__read_category_0_row(self, reset_singleton):
        async def async_mock():
            return {"rows": []}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await async_mock()
        else:
            _attr = asyncio.ensure_future(async_mock())

        attrs = {"query_tbl_with_payload.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)
        ret_val = await c_mgr._read_category(CAT_NAME)
        assert ret_val is None
        args, kwargs = storage_client_mock.query_tbl_with_payload.call_args
        assert 'configuration' == args[0]
        p = json.loads(args[1])
        assert {"return": ["key", "description", "value", "display_name",
                           {"column": "ts", "alias": "timestamp", "format": "YYYY-MM-DD HH24:MI:SS.MS"}],
                "where": {"column": "key", "condition": "=", "value": CAT_NAME}, "limit": 1} == p

    async def test__read_category_1_row(self, reset_singleton):
        async def async_mock():
            return {"rows": storage_result, "count": 1}

        storage_result = [{'display_name': CAT_NAME, 'key': CAT_NAME, 'description': 'Test Des',
                           'value': {'config_item': {'default': 'blah', 'value': 'blah', 'description': 'Des',
                                                     'type': 'string'}}}]

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await async_mock()
        else:
            _attr = asyncio.ensure_future(async_mock())

        attrs = {"query_tbl_with_payload.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)
        ret_val = await c_mgr._read_category(CAT_NAME)
        assert storage_result[0] == ret_val
        args, kwargs = storage_client_mock.query_tbl_with_payload.call_args
        assert 'configuration' == args[0]
        p = json.loads(args[1])
        assert {"return": ["key", "description", "value", "display_name",
                           {"column": "ts", "alias": "timestamp", "format": "YYYY-MM-DD HH24:MI:SS.MS"}],
                "where": {"column": "key", "condition": "=", "value": CAT_NAME},  "limit": 1} == p

    @pytest.mark.parametrize("value, expected_result", [
        (True, [('General', 'General', 'GEN'), ('Advanced', 'Advanced', 'ADV')]),
        (False, [('service', 'Fledge service', 'SERV'), ('rest_api', 'User REST API', 'API')])
    ])
    async def test__read_all_groups(self, reset_singleton, value, expected_result):
        @asyncio.coroutine
        def q_result(*args):
            table = args[0]
            payload = json.loads(args[1])
            if table == "configuration":
                assert {"return": ["key", "description", "display_name"]} == payload
                return {"rows": [{"key": "General", "description": "General", "display_name": "GEN"}, {"key": "Advanced", "description": "Advanced", "display_name": "ADV"}, {"key": "service", "description": "Fledge service", "display_name": "SERV"}, {"key": "rest_api", "description": "User REST API", "display_name": "API"}], "count": 4}

            if table == "category_children":
                assert {"return": ["child"], "modifier": "distinct"} == payload
                return {"rows": [{"child": "SMNTR"}, {"child": "service"}, {"child": "rest_api"}], "count": 3}

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(storage_client_mock, 'query_tbl_with_payload', side_effect=q_result) as query_tbl_patch:
            ret_val = await c_mgr._read_all_groups(root=value, children=False)
            assert expected_result == ret_val
        assert 2 == query_tbl_patch.call_count

    async def test__read_category_val_1_row(self, reset_singleton):
        async def mock_coro():
            return {'rows': [{'value': 'value1'}]}
        category_name = 'catname'

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"query_tbl_with_payload.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(PayloadBuilder, '__init__', return_value=None):
            with patch.object(PayloadBuilder, 'SELECT', return_value=PayloadBuilder) as pbselectpatch:
                with patch.object(PayloadBuilder, 'WHERE', return_value=PayloadBuilder) as pbwherepatch:
                    with patch.object(PayloadBuilder, 'payload', return_value=None) as pbpayloadpatch:
                        ret_val = await c_mgr._read_category_val(category_name)
                        assert 'value1' == ret_val
                    pbpayloadpatch.assert_called_once_with()
                pbwherepatch.assert_called_once_with(["key", "=", category_name])
            pbselectpatch.assert_called_once_with('value')
        storage_client_mock.query_tbl_with_payload.assert_called_once_with(
            'configuration', None)

    async def test__read_category_val_0_row(self, reset_singleton):
        async def mock_coro():
            return {'rows': []}

        category_name = 'catname'

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"query_tbl_with_payload.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(PayloadBuilder, '__init__', return_value=None):
            with patch.object(PayloadBuilder, 'SELECT', return_value=PayloadBuilder) as pbselectpatch:
                with patch.object(PayloadBuilder, 'WHERE', return_value=PayloadBuilder) as pbwherepatch:
                    with patch.object(PayloadBuilder, 'payload', return_value=None) as pbpayloadpatch:
                        ret_val = await c_mgr._read_category_val(category_name)
                        assert ret_val is None
                    pbpayloadpatch.assert_called_once_with()
                pbwherepatch.assert_called_once_with(["key", "=", category_name])
            pbselectpatch.assert_called_once_with('value')
        storage_client_mock.query_tbl_with_payload.assert_called_once_with(
            'configuration', None)

    async def test__read_item_val_0_row(self, reset_singleton):
        @asyncio.coroutine
        def mock_coro():
            return {'rows': []}

        category_name = 'catname'
        item_name = 'itemname'

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"query_tbl_with_payload.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)
        ret_val = await c_mgr._read_item_val(category_name, item_name)
        assert ret_val is None

    async def test__read_item_val_1_row(self, reset_singleton):
        @asyncio.coroutine
        def mock_coro():
            return {'rows': [{'value': 'value1'}]}

        category_name = 'catname'
        item_name = 'itemname'

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"query_tbl_with_payload.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)
        ret_val = await c_mgr._read_item_val(category_name, item_name)
        assert ret_val == 'value1'

    async def test__read_value_val_0_row(self, reset_singleton):
        @asyncio.coroutine
        def mock_coro():
            return {'rows': []}

        category_name = 'catname'
        item_name = 'itemname'

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"query_tbl_with_payload.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)
        ret_val = await c_mgr._read_value_val(category_name, item_name)
        assert ret_val is None

    async def test__read_value_val_1_row(self, reset_singleton):
        @asyncio.coroutine
        def mock_coro():
            return {'rows': [{'value': 'value1'}]}

        category_name = 'catname'
        item_name = 'itemname'

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"query_tbl_with_payload.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)
        ret_val = await c_mgr._read_value_val(category_name, item_name)
        assert ret_val == 'value1'

    async def test__update_value_val(self, reset_singleton):
        async def async_mock(return_value):
            return return_value

        async def mock_coro():
            return {"rows": []}

        category_name = 'catname'
        item_name = 'itemname'
        new_value_val = 'newval'

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
            _rv = await async_mock(None)
        else:
            _attr = asyncio.ensure_future(mock_coro())
            _rv = asyncio.ensure_future(async_mock(None))      

        attrs = {"query_tbl_with_payload.return_value": _attr, "update_tbl.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(AuditLogger, '__init__', return_value=None):
            with patch.object(AuditLogger, 'information', return_value=_rv) as auditinfopatch:
                await c_mgr._update_value_val(category_name, item_name, new_value_val)
        auditinfopatch.assert_called_once_with(
            'CONCH', {
                'category': category_name, 'item': item_name, 'oldValue': None, 'newValue': new_value_val})

    async def test__update_value_val_storageservererror(self, reset_singleton):
        async def mock_coro():
            return {"rows": []}

        category_name = 'catname'
        item_name = 'itemname'
        new_value_val = 'newval'

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"query_tbl_with_payload.return_value": _attr, "update_tbl.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(AuditLogger, '__init__', return_value=None):
            with patch.object(AuditLogger, 'information', return_value=None) as auditinfopatch:
                with patch.object(ConfigurationManager, '_update_value_val',
                                  side_effect=StorageServerError(None, None, None)) as createpatch:
                    with pytest.raises(StorageServerError):
                        await c_mgr._update_value_val(category_name, item_name, new_value_val)
                createpatch.assert_called_once_with('catname', 'itemname', 'newval')

        assert 0 == auditinfopatch.call_count

    async def test__update_value_val_keyerror(self, reset_singleton):
        async def mock_coro():
            return {"rows": []}

        category_name = 'catname'
        item_name = 'itemname'
        new_value_val = 'newval'

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"query_tbl_with_payload.return_value": _attr, "update_tbl.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(AuditLogger, '__init__', return_value=None):
            with patch.object(AuditLogger, 'information', return_value=None) as auditinfopatch:
                with patch.object(ConfigurationManager, '_update_value_val',
                                  side_effect=KeyError()) as createpatch:
                    with pytest.raises(KeyError):
                        await c_mgr._update_value_val(category_name, item_name, new_value_val)
                createpatch.assert_called_once_with('catname', 'itemname', 'newval')

        assert 0 == auditinfopatch.call_count

    async def test__update_category(self, reset_singleton):
        async def mock_coro():
            return {"response": "dummy"}

        category_name = 'catname'
        category_description = 'catdesc'
        category_val = 'catval'

        @asyncio.coroutine
        def mock_coro2():
            return category_val

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"update_tbl.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(PayloadBuilder, '__init__', return_value=None):
            with patch.object(PayloadBuilder, 'SET', return_value=PayloadBuilder) as pbsetpatch:
                with patch.object(PayloadBuilder, 'WHERE', return_value=PayloadBuilder) as pbwherepatch:
                    with patch.object(PayloadBuilder, 'payload', return_value=None) as pbpayloadpatch:
                        with patch.object(c_mgr, '_read_category_val', return_value=mock_coro2()) as readpatch:
                            await c_mgr._update_category(category_name, category_val, category_description)
                        readpatch.assert_called_once_with(category_name)
                    pbpayloadpatch.assert_called_once_with()
                pbwherepatch.assert_called_once_with(["key", "=", category_name])
            pbsetpatch.assert_called_once_with(description=category_description, value=category_val, display_name=category_name)
        storage_client_mock.update_tbl.assert_called_once_with('configuration', None)

    async def test__update_category_storageservererror(self, reset_singleton):
        async def mock_coro():
            return {"response": "dummy"}

        category_name = 'catname'
        category_description = 'catdesc'
        category_val = 'catval'

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"update_tbl.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(PayloadBuilder, '__init__', return_value=None):
            with patch.object(PayloadBuilder, 'SET', return_value=PayloadBuilder) as pbsetpatch:
                with patch.object(PayloadBuilder, 'WHERE', return_value=PayloadBuilder) as pbwherepatch:
                    with patch.object(PayloadBuilder, 'payload', return_value=None) as pbpayloadpatch:
                        with patch.object(ConfigurationManager, '_update_category',
                                          side_effect=StorageServerError(None, None, None)) as createpatch:
                            with pytest.raises(StorageServerError):
                                await c_mgr._update_category(category_name, category_val, category_description)
                        createpatch.assert_called_once_with('catname', 'catval', 'catdesc')
                    assert 0 == pbpayloadpatch.call_count
                assert 0 == pbwherepatch.call_count
            assert 0 == pbsetpatch.call_count
        assert 0 == storage_client_mock.update_tbl.call_count

    async def test__update_category_keyerror(self, reset_singleton):
        async def mock_coro():
            return {"noresponse": "dummy"}

        category_name = 'catname'
        category_description = 'catdesc'
        category_val = 'catval'

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"update_tbl.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(PayloadBuilder, '__init__', return_value=None):
            with patch.object(PayloadBuilder, 'SET', return_value=PayloadBuilder) as pbsetpatch:
                with patch.object(PayloadBuilder, 'WHERE', return_value=PayloadBuilder) as pbwherepatch:
                    with patch.object(PayloadBuilder, 'payload', return_value=None) as pbpayloadpatch:
                        with pytest.raises(KeyError):
                            await c_mgr._update_category(category_name, category_val, category_description)
                    pbpayloadpatch.assert_called_once_with()
                pbwherepatch.assert_called_once_with(["key", "=", category_name])
            pbsetpatch.assert_called_once_with(description=category_description, value=category_val, display_name=category_name)
        storage_client_mock.update_tbl.assert_called_once_with('configuration', None)

    async def test_get_category_child(self):
        async def async_mock(return_value):
            return return_value

        category_name = 'HTTP SOUTH'
        all_child_ret_val = [{'parent': 'south', 'child': category_name}]
        child_info_ret_val = [{'key': category_name, 'description': 'HTTP South Plugin', 'display_name': category_name}]

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock('bla')
            _rv2 = await async_mock(all_child_ret_val)
            _rv3 = await async_mock(child_info_ret_val)
        else:
            _rv1 = asyncio.ensure_future(async_mock('bla'))
            _rv2 = asyncio.ensure_future(async_mock(all_child_ret_val))
            _rv3 = asyncio.ensure_future(async_mock(child_info_ret_val))

        with patch.object(ConfigurationManager, '_read_category_val', return_value=_rv1) as patch_read_cat_val:
            with patch.object(ConfigurationManager, '_read_all_child_category_names', return_value=_rv2) as patch_read_all_child:
                with patch.object(ConfigurationManager, '_read_child_info', return_value=_rv3) as patch_read_child_info:
                    ret_val = await c_mgr.get_category_child(category_name)
                    assert [{'displayName': category_name, 'description': 'HTTP South Plugin', 'key': category_name}] == ret_val
                patch_read_child_info.assert_called_once_with([{'child': category_name, 'parent': 'south'}])
            patch_read_all_child.assert_called_once_with(category_name)
        patch_read_cat_val.assert_called_once_with(category_name)

    async def test_get_category_child_no_exist(self):
        async def async_mock(return_value):
            return return_value

        category_name = 'HTTP SOUTH'
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(None)
        else:
            _rv = asyncio.ensure_future(async_mock(None))

        with patch.object(ConfigurationManager, '_read_category_val', return_value=_rv) as patch_read_cat_val:
            with pytest.raises(ValueError) as excinfo:
                await c_mgr.get_category_child(category_name)
            assert 'No such {} category exist'.format(category_name) == str(excinfo.value)
        patch_read_cat_val.assert_called_once_with(category_name)

    @pytest.mark.parametrize("cat_name, children, message", [
        (1, ["coap"], 'category_name must be a string'),
        ("south", "coap", 'children must be a list')
    ])
    async def test_create_child_category_type_error(self, cat_name, children, message):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with pytest.raises(TypeError) as excinfo:
            await c_mgr.create_child_category(cat_name, children)
        assert message == str(excinfo.value)

    @pytest.mark.parametrize("ret_cat_name, ret_child_name, message", [
        (None, None, 'No such south category exist'),
        ("south", None, 'No such coap child exist')
    ])
    async def test_create_child_category_no_exists(self, ret_cat_name, ret_child_name, message):
        @asyncio.coroutine
        def q_result(*args):
            if args[0] == cat_name:
                return async_mock(ret_cat_name)
            if args[0] == child_name:
                return async_mock(ret_child_name)

        async def async_mock(return_value):
            return return_value

        cat_name = 'south'
        child_name = ["coap"]
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(ConfigurationManager, '_read_category_val', side_effect=q_result):
            with pytest.raises(ValueError) as excinfo:
                await c_mgr.create_child_category(cat_name, child_name)
            assert message == str(excinfo.value)

    async def test_create_child_category(self, reset_singleton):
        @asyncio.coroutine
        def q_result(*args):
            if args[0] == cat_name:
                return async_mock('blah1')
            if args[0] == child_name:
                return async_mock('blah2')

        async def async_mock(return_value):
            return return_value

        cat_name = 'south'
        child_name = "coap"
        all_child_ret_val = [{'parent': cat_name, 'child': 'http'}]

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock('inserted')
            _rv2 = await async_mock(all_child_ret_val)
            _sr = await async_mock((False, None, None, None))
        else:
            _rv1 = asyncio.ensure_future(async_mock('inserted'))
            _rv2 = asyncio.ensure_future(async_mock(all_child_ret_val))
            _sr = asyncio.ensure_future(async_mock((False, None, None, None)))
        
        with patch.object(ConfigurationManager, '_read_category_val', side_effect=q_result):
            with patch.object(ConfigurationManager, '_read_all_child_category_names',
                              return_value=_rv2) as patch_readall_child:
                with patch.object(ConfigurationManager, '_create_child',
                                  return_value=_rv1) as patch_create_child:
                    with patch.object(ConfigurationManager, 'search_for_ACL_recursive_from_cat_name',
                                      return_value=_sr) as searchaclpatch:
                        ret_val = await c_mgr.create_child_category(cat_name, [child_name])
                        assert {'children': ['http', 'coap']} == ret_val
                    searchaclpatch.assert_has_calls([call(cat_name), call(child_name)])
            patch_readall_child.assert_called_once_with(cat_name)
        patch_create_child.assert_called_once_with(cat_name, child_name)

    async def test_create_child_category_if_exists(self, reset_singleton):
        @asyncio.coroutine
        def q_result(*args):
            if args[0] == cat_name:
                return async_mock('blah1')
            if args[0] == child_name:
                return async_mock('blah2')

        async def async_mock(return_value):
            return return_value

        cat_name = 'south'
        child_name = "coap"
        all_child_ret_val = [{'parent': cat_name, 'child': child_name}]

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(all_child_ret_val)
            _sr = await async_mock((False, None, None, None))
        else:
            _rv = asyncio.ensure_future(async_mock(all_child_ret_val))
            _sr = asyncio.ensure_future(async_mock((False, None, None, None)))
        
        with patch.object(ConfigurationManager, '_read_category_val', side_effect=q_result):
            with patch.object(ConfigurationManager, '_read_all_child_category_names',
                              return_value=_rv) as patch_readall_child:
                with patch.object(ConfigurationManager, 'search_for_ACL_recursive_from_cat_name',
                                  return_value=_sr) as searchaclpatch:
                    ret_val = await c_mgr.create_child_category(cat_name, [child_name])
                    assert {'children': ['coap']} == ret_val
                searchaclpatch.assert_has_calls([call(cat_name)])
            patch_readall_child.assert_called_once_with(cat_name)

    @pytest.mark.parametrize("cat_name, child_name, message", [
        (1, "coap", 'category_name must be a string'),
        ("south", 1, 'child_category must be a string')
    ])
    async def test_delete_child_category_type_error(self, cat_name, child_name, message):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with pytest.raises(TypeError) as excinfo:
            await c_mgr.delete_child_category(cat_name, child_name)
        assert message == str(excinfo.value)

    @pytest.mark.parametrize("ret_cat_name, ret_child_name, message", [
        (None, None, 'No such south category exist'),
        ("south", None, 'No such coap child exist')
    ])
    async def test_delete_child_category_no_exists(self, ret_cat_name, ret_child_name, message):
        @asyncio.coroutine
        def q_result(*args):
            if args[0] == cat_name:
                return async_mock(ret_cat_name)
            if args[0] == child_name:
                return async_mock(ret_child_name)

        async def async_mock(return_value):
            return return_value

        cat_name = 'south'
        child_name = 'coap'
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(ConfigurationManager, '_read_category_val', side_effect=q_result):
            with pytest.raises(ValueError) as excinfo:
                await c_mgr.delete_child_category(cat_name, child_name)
            assert message == str(excinfo.value)

    async def test_delete_child_category(self, reset_singleton):
        async def mock_coro():
            return expected_result

        @asyncio.coroutine
        def q_result(*args):
            if args[0] == cat_name:
                return async_mock('blah1')
            if args[0] == child_name:
                return async_mock('blah2')

        async def async_mock(return_value):
            return return_value

        expected_result = {"response": "deleted", "rows_affected": 1}
        cat_name = 'south'
        child_name = 'coap'
        all_child_ret_val = [{'parent': cat_name, 'child': child_name}]
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
            _rv = await async_mock(all_child_ret_val)
        else:
            _attr = asyncio.ensure_future(mock_coro())
            _rv = asyncio.ensure_future(async_mock(all_child_ret_val))
        
        attrs = {"delete_from_tbl.return_value": _attr}
        payload = {"where": {"column": "parent", "condition": "=", "value": "south", "and": {"column": "child", "condition": "=", "value": "coap"}}}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(ConfigurationManager, '_read_category_val', side_effect=q_result):
            with patch.object(ConfigurationManager, '_read_all_child_category_names',
                              return_value=_rv) as patch_read_all_child:
                ret_val = await c_mgr.delete_child_category(cat_name, child_name)
                assert [child_name] == ret_val
            patch_read_all_child.assert_called_once_with(cat_name)
        del_args, del_kwargs = storage_client_mock.delete_from_tbl.call_args
        assert 'category_children' == del_args[0]
        assert payload == json.loads(del_args[1])

    async def test_delete_child_category_key_error(self, reset_singleton):
        async def mock_coro():
            return expected_result

        @asyncio.coroutine
        def q_result(*args):
            if args[0] == cat_name:
                return async_mock('blah1')
            if args[0] == child_name:
                return async_mock('blah2')

        async def async_mock(return_value):
            return return_value

        expected_result = {"message": "blah"}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"delete_from_tbl.return_value": _attr}
        cat_name = 'south'
        child_name = 'coap'
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(ConfigurationManager, '_read_category_val', side_effect=q_result):
            with pytest.raises(ValueError) as excinfo:
                await c_mgr.delete_child_category(cat_name, child_name)
            assert 'blah' == str(excinfo.value)

    async def test_delete_child_category_storage_exception(self, reset_singleton):
        @asyncio.coroutine
        def q_result(*args):
            if args[0] == cat_name:
                return async_mock('blah1')
            if args[0] == child_name:
                return async_mock('blah2')

        async def async_mock(return_value):
            return return_value

        cat_name = 'south'
        child_name = 'coap'
        msg = {"entryPoint": "delete", "message": "failed"}
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with patch.object(ConfigurationManager, '_read_category_val', side_effect=q_result):
            with patch.object(storage_client_mock, 'delete_from_tbl', side_effect=StorageServerError(code=400,
                                                                                                     reason="blah", error=msg)):
                with pytest.raises(ValueError) as excinfo:
                    await c_mgr.delete_child_category(cat_name, child_name)
                assert str(msg) == str(excinfo.value)

    async def test_delete_parent_category(self, reset_singleton):
        async def mock_coro():
            return expected_result

        async def async_mock(return_value):
            return return_value

        expected_result = {"response": "deleted", "rows_affected": 1}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
            _rv = await async_mock('bla')
        else:
            _attr = asyncio.ensure_future(mock_coro())
            _rv = asyncio.ensure_future(async_mock('bla'))        

        attrs = {"delete_from_tbl.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(ConfigurationManager, '_read_category_val', return_value=_rv) as patch_read_cat_val:
            ret_val = await c_mgr.delete_parent_category("south")
            assert expected_result == ret_val
        patch_read_cat_val.assert_called_once_with('south')
        storage_client_mock.delete_from_tbl.assert_called_once_with('category_children',
                                                                    '{"where": {"column": "parent", "condition": "=", "value": "south"}}')

    async def test_delete_parent_category_bad_cat_name(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with pytest.raises(TypeError) as excinfo:
            await c_mgr.delete_parent_category(1)
        assert 'category_name must be a string' == str(excinfo.value)

    async def test_delete_parent_category_no_exists(self):
        async def async_mock(return_value):
            return return_value

        category_name = 'blah'
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(None)
        else:
            _rv = asyncio.ensure_future(async_mock(None))

        with patch.object(ConfigurationManager, '_read_category_val', return_value=_rv) as patch_read_cat_val:
            with pytest.raises(ValueError) as excinfo:
                await c_mgr.delete_parent_category(category_name)
            assert 'No such {} category exist'.format(category_name) == str(excinfo.value)
        patch_read_cat_val.assert_called_once_with(category_name)

    async def test_delete_parent_category_key_error(self, reset_singleton):
        @asyncio.coroutine
        def mock_coro():
            return {"message": "blah"}

        async def async_mock(return_value):
            return return_value

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
            _rv = await async_mock('blah')
        else:
            _attr = asyncio.ensure_future(mock_coro())
            _rv = asyncio.ensure_future(async_mock('blah')) 

        attrs = {"delete_from_tbl.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)

        with patch.object(ConfigurationManager, '_read_category_val', return_value=_rv) as patch_read_cat_val:
            with pytest.raises(ValueError) as excinfo:
                await c_mgr.delete_parent_category("south")
            assert 'blah' == str(excinfo.value)
        patch_read_cat_val.assert_called_once_with("south")

    async def test_delete_parent_category_storage_exception(self, reset_singleton):
        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        msg = {"entryPoint": "delete", "message": "failed"}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock('blah')
        else:
            _rv = asyncio.ensure_future(async_mock('blah'))

        with patch.object(ConfigurationManager, '_read_category_val', return_value=_rv) as patch_read_cat_val:
            with patch.object(storage_client_mock, 'delete_from_tbl', side_effect=StorageServerError(code=400,
                                                                                                     reason="blah", error=msg)):
                with pytest.raises(ValueError) as excinfo:
                    await c_mgr.delete_parent_category("south")
                assert str(msg) == str(excinfo.value)
        patch_read_cat_val.assert_called_once_with("south")

    async def test_delete_category_and_children_recursively(self, mocker, reset_singleton):
        @asyncio.coroutine
        def mock_coro(a, b):
            return expected_result

        async def async_mock(return_value):
            return return_value

        async def mock_read_all_child_category_names(cat):
            """
            Mimics 
                     G      I
                      \    /
                       F  H
                        \/
                        E    
                       /    M
                      /    / 
                A -- B -- C  -- D 
                \     \
                 \     N
                  \
                   \   K
                    \ /
                     J\
                       \
                        L
            :param cat: 
            :return: 
            """
            if cat == "A":
                return [{"parent": 'A', "child": 'B'}, {"parent": 'A', "child": 'J'}]
            if cat == "B":
                return [{"parent": 'B', "child": 'E'}, {"parent": 'B', "child": 'N'}, {"parent": 'B', "child": 'C'}]
            if cat == "C":
                return [{"parent": 'C', "child": 'M'}, {"parent": 'C', "child": 'D'}]
            if cat == "D":
                return []
            if cat == "E":
                return [{"parent": 'E', "child": 'F'}, {"parent": 'E', "child": 'H'}]
            if cat == "F":
                return [{"parent": 'F', "child": 'G'}]
            if cat == "G":
                return []
            if cat == "H":
                return [{"parent": 'H', "child": 'I'}]
            if cat == "I":
                return []
            if cat == "J":
                return [{"parent": 'J', "child": 'K'}, {"parent": 'J', "child": 'L'}]
            if cat == "K":
                return []
            if cat == "L":
                return []
            if cat == "M":
                return []
            if cat == "N":
                return []

        expected_result = {"response": "deleted", "rows_affected": 1}
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        patch_delete_from_tbl = mocker.patch.object(storage_client_mock, 'delete_from_tbl', side_effect=mock_coro)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock('bla')
            _sr = await async_mock((False, None, None, None))
        else:
            _rv = asyncio.ensure_future(async_mock('bla'))
            _sr = asyncio.ensure_future(async_mock((False, None, None, None)))
        
        c_mgr = ConfigurationManager(storage_client_mock)
        patch_read_cat_val = mocker.patch.object(ConfigurationManager, '_read_category_val',
                                                 return_value=_rv)
        mocker.patch.object(ConfigurationManager, '_read_all_child_category_names',
                            side_effect=mock_read_all_child_category_names)
        patch_fetch_descendents = mocker.patch.object(ConfigurationManager, '_fetch_descendents',
                                                      return_value=_rv)

        mocker.patch.object(AuditLogger, '__init__', return_value=None)
        audit_info = mocker.patch.object(AuditLogger, 'information', return_value=_rv)

        acl_search_calls = [call('G'), call('F'), call('I'), call('H'),
                            call('E'), call('N'), call('M'), call('D'),
                            call('C'), call('B'), call('K'), call('L'),
                            call('J'), call('A')]
        with patch.object(ConfigurationManager, 'search_for_ACL_single',
                          return_value=_sr) as searchaclpatch:
            ret_val = await c_mgr.delete_category_and_children_recursively("A")
            assert expected_result == ret_val
        searchaclpatch.assert_has_calls(acl_search_calls)

        patch_read_cat_val.assert_called_once_with('A')
        patch_fetch_descendents.assert_called_once_with('A')
        calls = [call('category_children', '{"where": {"column": "child", "condition": "=", "value": "G"}}'),
                 call('configuration', '{"where": {"column": "key", "condition": "=", "value": "G"}}'),
                 call('category_children', '{"where": {"column": "child", "condition": "=", "value": "F"}}'),
                 call('configuration', '{"where": {"column": "key", "condition": "=", "value": "F"}}'),
                 call('category_children', '{"where": {"column": "child", "condition": "=", "value": "I"}}'),
                 call('configuration', '{"where": {"column": "key", "condition": "=", "value": "I"}}'),
                 call('category_children', '{"where": {"column": "child", "condition": "=", "value": "H"}}'),
                 call('configuration', '{"where": {"column": "key", "condition": "=", "value": "H"}}'),
                 call('category_children', '{"where": {"column": "child", "condition": "=", "value": "E"}}'),
                 call('configuration', '{"where": {"column": "key", "condition": "=", "value": "E"}}'),
                 call('category_children', '{"where": {"column": "child", "condition": "=", "value": "N"}}'),
                 call('configuration', '{"where": {"column": "key", "condition": "=", "value": "N"}}'),
                 call('category_children', '{"where": {"column": "child", "condition": "=", "value": "M"}}'),
                 call('configuration', '{"where": {"column": "key", "condition": "=", "value": "M"}}'),
                 call('category_children', '{"where": {"column": "child", "condition": "=", "value": "D"}}'),
                 call('configuration', '{"where": {"column": "key", "condition": "=", "value": "D"}}'),
                 call('category_children', '{"where": {"column": "child", "condition": "=", "value": "C"}}'),
                 call('configuration', '{"where": {"column": "key", "condition": "=", "value": "C"}}'),
                 call('category_children', '{"where": {"column": "child", "condition": "=", "value": "B"}}'),
                 call('configuration', '{"where": {"column": "key", "condition": "=", "value": "B"}}'),
                 call('category_children', '{"where": {"column": "child", "condition": "=", "value": "K"}}'),
                 call('configuration', '{"where": {"column": "key", "condition": "=", "value": "K"}}'),
                 call('category_children', '{"where": {"column": "child", "condition": "=", "value": "L"}}'),
                 call('configuration', '{"where": {"column": "key", "condition": "=", "value": "L"}}'),
                 call('category_children', '{"where": {"column": "child", "condition": "=", "value": "J"}}'),
                 call('configuration', '{"where": {"column": "key", "condition": "=", "value": "J"}}'),
                 call('category_children', '{"where": {"column": "child", "condition": "=", "value": "A"}}'),
                 call('configuration', '{"where": {"column": "key", "condition": "=", "value": "A"}}')]

        audit_calls = [call('CONCH', {'categoryDeleted': 'G'}),
                       call('CONCH', {'categoryDeleted': 'F'}),
                       call('CONCH', {'categoryDeleted': 'I'}),
                       call('CONCH', {'categoryDeleted': 'H'}),
                       call('CONCH', {'categoryDeleted': 'E'}),
                       call('CONCH', {'categoryDeleted': 'N'}),
                       call('CONCH', {'categoryDeleted': 'M'}),
                       call('CONCH', {'categoryDeleted': 'D'}),
                       call('CONCH', {'categoryDeleted': 'C'}),
                       call('CONCH', {'categoryDeleted': 'B'}),
                       call('CONCH', {'categoryDeleted': 'K'}),
                       call('CONCH', {'categoryDeleted': 'L'}),
                       call('CONCH', {'categoryDeleted': 'J'}),
                       call('CONCH', {'categoryDeleted': 'A'})]
        
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            await patch_delete_from_tbl.has_calls(calls, any_order=True)
            await audit_info.has_calls(audit_calls, any_order=True)
        else:
            patch_delete_from_tbl.has_calls(calls, any_order=True)
            audit_info.has_calls(audit_calls, any_order=True)

    async def test_delete_category_and_children_recursively_exception(self, mocker, reset_singleton):
        @asyncio.coroutine
        def mock_coro(a, b):
            return expected_result

        async def async_mock(return_value):
            return return_value

        @asyncio.coroutine
        def mock_read_all_child_category_names(cat):
            """
            Mimics 
                     G      I
                      \    /
                       F  H
                        \/
                        E    
                       /    M
                      /    / 
                A -- B -- C  -- D 
                \     \
                 \     N
                  \
                   \   K
                    \ /
                     North\
                           \
                            L
            :param cat: 
            :return: 
            """
            if cat == "A":
                return [{"parent": 'A', "child": 'B'}, {"parent": 'A', "child": "North"}]
            if cat == "B":
                return [{"parent": 'B', "child": 'E'}, {"parent": 'B', "child": 'N'}, {"parent": 'B', "child": 'C'}]
            if cat == "C":
                return [{"parent": 'C', "child": 'M'}, {"parent": 'C', "child": 'D'}]
            if cat == "D":
                return []
            if cat == "E":
                return [{"parent": 'E', "child": 'F'}, {"parent": 'E', "child": 'H'}]
            if cat == "F":
                return [{"parent": 'F', "child": 'G'}]
            if cat == "G":
                return []
            if cat == "H":
                return [{"parent": 'H', "child": 'I'}]
            if cat == "I":
                return []
            if cat == "North":
                return [{"parent": "North", "child": 'K'}, {"parent": "North", "child": 'L'}]
            if cat == "K":
                return []
            if cat == "L":
                return []
            if cat == "M":
                return []
            if cat == "N":
                return []

        expected_result = {"response": "deleted", "rows_affected": 1}
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        mocker.patch.object(storage_client_mock, 'delete_from_tbl', side_effect=mock_coro)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock('bla')
        else:
            _rv = asyncio.ensure_future(async_mock('bla'))
        
        c_mgr = ConfigurationManager(storage_client_mock)
        mocker.patch.object(ConfigurationManager, '_read_category_val', return_value=_rv)
        mocker.patch.object(ConfigurationManager, '_read_all_child_category_names',
                            side_effect=mock_read_all_child_category_names)

        mocker.patch.object(AuditLogger, '__init__', return_value=None)
        mocker.patch.object(AuditLogger, 'information', return_value=_rv)
        msg = "Reserved category found in descendents of A - ['B', 'E', 'F', 'G', 'H', 'I', 'N', 'C', 'M', 'D', " \
              "'North', 'K', 'L']"

        with pytest.raises(ValueError) as excinfo:
            await c_mgr.delete_category_and_children_recursively("A")
        assert str(msg) == str(excinfo.value)

    async def test__read_all_child_category_names(self, reset_singleton):
        async def mock_coro():
            return {'rows': [{'parent': 'south', 'child': 'http'}], 'count': 1}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"query_tbl_with_payload.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)
        payload = {"return": ["parent", "child"], "where": {"value": "south", "condition": "=", "column": "parent"}, "sort": {"column": "id", "direction": "asc"}}
        ret_val = await c_mgr._read_all_child_category_names('south')
        assert [{'parent': 'south', 'child': 'http'}] == ret_val
        args, kwargs = storage_client_mock.query_tbl_with_payload.call_args
        assert 'category_children' == args[0]
        assert payload == json.loads(args[1])

    async def test__read_child_info(self, reset_singleton):
        async def mock_coro():
            return {'rows': [{'description': 'HTTP South Plugin', 'key': 'HTTP SOUTH'}], 'count': 1}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"query_tbl_with_payload.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        child_cat_names = [{'child': 'HTTP SOUTH', 'parent': 'south'}]
        payload = {"return": ["key", "description", "display_name"], "where": {"column": "key", "condition": "=",
                                                                               "value": "HTTP SOUTH"}}
        c_mgr = ConfigurationManager(storage_client_mock)
        ret_val = await c_mgr._read_child_info(child_cat_names)
        assert [{'description': 'HTTP South Plugin', 'key': 'HTTP SOUTH'}] == ret_val
        args, kwargs = storage_client_mock.query_tbl_with_payload.call_args
        assert 'configuration' == args[0]
        assert payload == json.loads(args[1])

    async def test__create_child(self):
        async def mock_coro():
            return {"response": "inserted", "rows_affected": 1}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"insert_into_tbl.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)
        c_mgr = ConfigurationManager(storage_client_mock)
        payload = {"child": "http", "parent": "south"}

        ret_val = await c_mgr._create_child("south", "http")
        assert 'inserted' == ret_val

        args, kwargs = storage_client_mock.insert_into_tbl.call_args
        assert 'category_children' == args[0]
        assert payload == json.loads(args[1])

    async def test__create_child_key_error(self, reset_singleton):
        async def mock_coro():
            return {"message": "blah"}

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _attr = await mock_coro()
        else:
            _attr = asyncio.ensure_future(mock_coro())

        attrs = {"insert_into_tbl.return_value": _attr}
        storage_client_mock = MagicMock(spec=StorageClientAsync, **attrs)

        c_mgr = ConfigurationManager(storage_client_mock)
        with pytest.raises(ValueError) as excinfo:
            await c_mgr._create_child("south", "http")
        assert 'blah' == str(excinfo.value)

    async def test__create_child_storage_exception(self, reset_singleton):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        msg = {"entryPoint": "insert", "message": "UNIQUE constraint failed"}
        with patch.object(storage_client_mock, 'insert_into_tbl', side_effect=StorageServerError(code=400, reason="blah", error=msg)):
            with pytest.raises(ValueError) as excinfo:
                await c_mgr._create_child("south", "http")
            assert str(msg) == str(excinfo.value)

    @pytest.mark.parametrize("item_type, item_val, result", [
        ("boolean", "True", "true"),
        ("boolean", "true", "true"),
        ("boolean", "false", "false"),
        ("boolean", "False", "false")
    ])
    async def test__clean(self, item_type, item_val, result):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        assert result == c_mgr._clean(item_type, item_val)

    @pytest.mark.parametrize("item_type, item_val, result", [
        ("boolean", "false", True),
        ("boolean", "true", True),
        ("integer", "123", True),
        ("float", "123456", True),
        ("float", "0", True),
        ("float", "NaN", True),
        ("float", "123.456", True),
        ("float", "123.E4", True),
        ("float", ".1", True),
        ("float", "6.523e-07", True),
        ("float", "6e7777", True),
        ("float", "1.79e+308", True),
        ("float", "infinity", True),
        ("float", "0E0", True),
        ("float", "+1e1", True),
        ("IPv4", "127.0.0.1", ipaddress.IPv4Address('127.0.0.1')),
        ("IPv6", "2001:db8::", ipaddress.IPv6Address('2001:db8::')),
        ("JSON", {}, True),  # allow a dict
        ("JSON", "{}", True),
        ("JSON", "1", True),
        ("JSON", "[]", True),
        ("JSON", "1.2", True),
        ("JSON", "{\"age\": 31}", True),
        ("URL", "http://somevalue.do", True),
        ("URL", "http://www.example.com", True),
        ("URL", "https://www.example.com", True),
        ("URL", "http://blog.example.com", True),
        ("URL", "http://www.example.com/product", True),
        ("URL", "http://www.example.com/products?id=1&page=2", True),
        ("URL", "http://255.255.255.255", True),
        ("URL", "http://255.255.255.255:8080", True),
        ("URL", "http://127.0.0.1:8080", True),
        ("URL", "http://localhost", True),
        ("URL", "http://0.0.0.0:8081", True),
        ("URL", "http://fe80::4", True),
        ("URL", "https://pi-server:5460/ingress/messages", True),
        ("URL", "https://dat-a.osisoft.com/api/omf", True),
        ("URL", "coap://host", True),
        ("URL", "coap://host.co.in", True),
        ("URL", "coaps://host:6683", True),
        ("password", "not implemented", None),
        ("X509 certificate", "not implemented", None),
        ("northTask", "valid_north_task", True),
        ("listSize", "5", True),
        ("listSize", "0", True)
    ])
    async def test__validate_type_value(self, item_type, item_val, result):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        assert result == c_mgr._validate_type_value(item_type, item_val)

    @pytest.mark.parametrize("item_type, item_val", [
        ("float", ""),
        ("float", "nana"),
        ("float", "1,234"),
        ("float", "NULL"),
        ("float", ",1"),
        ("float", "123.EE4"),
        ("float", "12.34.56"),
        ("float", "1,234"),
        ("float", "#12"),
        ("float", "12%"),
        ("float", "x86E0"),
        ("float", "86-5"),
        ("float", "True"),
        ("float", "+1e1.3"),
        ("float", "-+1"),
        ("float", "(1)"),
        ("boolean", "blah"),
        ("JSON", "Blah"),
        ("JSON", True),
        ("JSON", "True"),
        ("JSON", []),
        ("JSON", None),
        ("URL", "blah"),
        ("URL", "example.com"),
        ("URL", "123:80"),
        ("listSize", "Blah"),
        ("listSize", "None")
        # TODO: can not use urlopen hence we may want to check
        # result.netloc with some regex, but limited
        # ("URL", "http://somevalue.a"),
        # ("URL", "http://25.25.25. :80"),
        # ("URL", "http://25.25.25.25: 80"),
        # ("URL", "http://www.example.com | http://www.example2.com")
    ])
    async def test__validate_type_value_bad_data(self, item_type, item_val):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        assert c_mgr._validate_type_value(item_type, item_val) is False

    @pytest.mark.parametrize("cat_info, config_item_list, exc_type, exc_msg", [
        (None, {}, NameError, "No such Category found for testcat"),
        ({'enableHttp': {'default': 'true', 'description': 'Enable HTTP', 'type': 'boolean', 'value': 'true'}},
         {"blah": "12"}, KeyError, "'blah config item not found'"),
        ({'enableHttp': {'default': 'true', 'description': 'Enable HTTP', 'type': 'boolean', 'value': 'true'}},
         {"enableHttp": False}, TypeError, "new value should be of type string"),
        ({'authentication': {'default': 'optional', 'options': ['mandatory', 'optional'], 'type': 'enumeration',
                             'description': 'API Call Authentication', 'value': 'optional'}}, {"authentication": ""},
         ValueError, "entry_val cannot be empty"),
        ({'authentication': {'default': 'optional', 'options': ['mandatory', 'optional'], 'type': 'enumeration',
                             'description': 'API Call Authentication', 'value': 'optional'}},
         {"authentication": "false"}, ValueError, "new value does not exist in options enum"),
        ({'authProviders': {'default': '{"providers": ["username", "ldap"] }',
                            'description': 'Authentication providers to use for the interface', 'type': 'JSON',
                            'value': '{"providers": ["username", "ldap"] }'}},
         {"authProviders": 3}, TypeError, "new value should be a valid dict Or a string literal, in double quotes"),
        ({'enableHttp': {'default': 'true', 'description': 'Enable HTTP', 'type': 'boolean', 'value': 'true'}},
         {"enableHttp": "blah"}, TypeError, "Unrecognized value name for item_name enableHttp"),
        ({'asset': {'default': 'sinusoid', 'description': 'Asset Name', 'type': 'string', 'value': 'sinusoid',
                    'mandatory': 'true'}}, {"asset": ''}, ValueError, "A value must be given for asset"),
        ({'datapoint': {'default': 'rw', 'description': 'Datapoint Name', 'type': 'string', 'value': 'rw',
                        'mandatory': 'true'}}, {"datapoint": ' '}, ValueError, "A value must be given for datapoint"),
        ({'testJSON': {'default': '{"foo": "bar"}', 'description': 'Test JSON', 'type': 'JSON',
                       'value': '{"foo": "bar"}', 'mandatory': 'true'}}, {"testJSON": ' '},
         TypeError, "Unrecognized value name for item_name testJSON"),
        ({'testJSON': {'default': '{"foo": "bar"}', 'description': 'Test JSON', 'type': 'JSON',
                       'value': '{"foo": "bar"}', 'mandatory': 'true'}}, {"testJSON": 'blah'},
         TypeError, "Unrecognized value name for item_name testJSON"),
        ({'testJSON': {'default': '{"foo": "bar"}', 'description': 'Test JSON', 'type': 'JSON',
                       'value': '{"foo": "bar"}', 'mandatory': 'true'}}, {"testJSON": {}},
         ValueError, "Dict cannot be set as empty. A value must be given for testJSON"),
        ({ITEM_NAME: {'default': '[\"foo\": \"bar\"]', 'description': 'Test list', 'type': 'list',
                      "items": "enumeration", 'value': '[\"foo\": \"bar\"]', 'options': ['foo', 'bar']}},
         {ITEM_NAME: ""}, TypeError, "Malformed payload for given testcat category"),
        ({ITEM_NAME: {'default': '{"key1": "a","key2": "b"}', 'description': 'Test Kvlist', 'type': 'kvlist',
                      "items": "enumeration", 'value': '{"key1": "a","key2": "b"}', 'options': ['b', 'a']}},
         {ITEM_NAME: ""}, TypeError, "Malformed payload for given testcat category")
    ])
    async def test_update_configuration_item_bulk_exceptions(self, cat_info, config_item_list, exc_type, exc_msg,
                                                             category_name='testcat'):
        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(cat_info)
        else:
            _rv = asyncio.ensure_future(async_mock(cat_info))

        with patch.object(c_mgr, 'get_category_all_items', return_value=_rv) as patch_get_all_items:
            with patch.object(_logger, 'exception') as patch_log_exc:
                with pytest.raises(Exception) as exc_info:
                    await c_mgr.update_configuration_item_bulk(category_name, config_item_list)
                assert exc_type == exc_info.type
                assert exc_msg == str(exc_info.value)
            assert 1 == patch_log_exc.call_count
        patch_get_all_items.assert_called_once_with(category_name)

    async def test_update_configuration_item_bulk(self, category_name='rest_api'):
        async def async_mock(return_value):
            return return_value

        cat_info = {'enableHttp': {'default': 'true', 'description': 'Enable HTTP', 'type': 'boolean', 'value': 'true'}}
        config_item_list = {"enableHttp": "false"}
        update_result = {"response": "updated", "rows_affected": 1}
        read_val = {'allowPing': {'default': 'true', 'description': 'Allow access to ping', 'value': 'true', 'type': 'boolean'},
                    'enableHttp': {'default': 'true', 'description': 'Enable HTTP', 'value': 'false', 'type': 'boolean'}}
        payload = {'updates': [{'json_properties': [{'path': ['enableHttp', 'value'], 'column': 'value', 'value': 'false'}],
                                'return': ['key', 'description', {'format': 'YYYY-MM-DD HH24:MI:SS.MS', 'column': 'ts'}, 'value'],
                                'where': {'value': 'rest_api', 'column': 'key', 'condition': '='}}]}
        audit_details = {'items': {'enableHttp': {'oldValue': 'true', 'newValue': 'false'}}, 'category': category_name}
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock(cat_info)
            _rv2 = await async_mock(update_result)
            _rv3 = await async_mock(read_val)
            _rv4 = await async_mock(None)
        else:
            _rv1 = asyncio.ensure_future(async_mock(cat_info))
            _rv2 = asyncio.ensure_future(async_mock(update_result))
            _rv3 = asyncio.ensure_future(async_mock(read_val))
            _rv4 = asyncio.ensure_future(async_mock(None))

        with patch.object(c_mgr, 'get_category_all_items', return_value=_rv1) as patch_get_all_items:
            with patch.object(c_mgr._storage, 'update_tbl', return_value=_rv2) as patch_update:
                with patch.object(c_mgr, '_read_category_val', return_value=_rv3) as patch_read_val:
                    with patch.object(AuditLogger, '__init__', return_value=None):
                        with patch.object(AuditLogger, 'information', return_value=_rv4) as patch_audit:
                            with patch.object(ConfigurationManager, '_run_callbacks', return_value=_rv4) \
                                    as patch_callback:
                                await c_mgr.update_configuration_item_bulk(category_name, config_item_list)
                            patch_callback.assert_called_once_with(category_name)
                        patch_audit.assert_called_once_with('CONCH', audit_details)
                patch_read_val.assert_called_once_with(category_name)
            args, kwargs = patch_update.call_args
            assert 'configuration' == args[0]
            assert payload == json.loads(args[1])
        patch_get_all_items.assert_called_once_with(category_name)

    async def test_update_configuration_item_bulk_no_change(self, category_name='rest_api'):
        async def async_mock(return_value):
            return return_value

        cat_info = {'enableHttp': {'default': 'true', 'description': 'Enable HTTP', 'type': 'boolean', 'value': 'true'}}
        config_item_list = {"enableHttp": "true"}
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(cat_info)
        else:
            _rv = asyncio.ensure_future(async_mock(cat_info))

        with patch.object(c_mgr, 'get_category_all_items', return_value=_rv) as patch_get_all_items:
            with patch.object(c_mgr._storage, 'update_tbl') as patch_update:
                with patch.object(AuditLogger, 'information') as patch_audit:
                    with patch.object(ConfigurationManager, '_run_callbacks') as patch_callback:
                        result = await c_mgr.update_configuration_item_bulk(category_name, config_item_list)
                        assert result is None
                    patch_callback.assert_not_called()
                patch_audit.assert_not_called()
            patch_update.assert_not_called()
        patch_get_all_items.assert_called_once_with(category_name)

    async def test_update_configuration_item_bulk_dict_no_change(self, category_name='rest_api'):
        async def async_mock(return_value):
            return return_value

        cat_info = {'providers': {'default': '{"providers": ["username", "ldap"] }', 'description': 'descr',
                                  'type': 'JSON', 'value': '{"providers": ["username", "ldap"] }'}}
        config_item_list = {"providers": {"providers": ["username", "ldap"]}}
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(cat_info)
        else:
            _rv = asyncio.ensure_future(async_mock(cat_info))

        with patch.object(c_mgr, 'get_category_all_items', return_value=_rv) as patch_get_all_items:
            with patch.object(c_mgr._storage, 'update_tbl') as patch_update:
                with patch.object(AuditLogger, 'information') as patch_audit:
                    with patch.object(ConfigurationManager, '_run_callbacks') as patch_callback:
                        result = await c_mgr.update_configuration_item_bulk(category_name, config_item_list)
                        assert result is None
                    patch_callback.assert_not_called()
                patch_audit.assert_not_called()
            patch_update.assert_not_called()
        patch_get_all_items.assert_called_once_with(category_name)

    async def test_update_configuration_item_bulk_dict_change(self, category_name='rest_api'):
        async def async_mock(return_value):
            return return_value

        cat_info = {'providers': {'default': '{"providers": ["username", "ldap"] }', 'description': 'descr',
                                  'type': 'JSON', 'value': '{"providers": ["username", "ldap"] }'}}
        config_item_list = {"providers": {"providers": ["username", "ldap_new"]}}

        update_result = {"response": "updated", "rows_affected": 1}
        read_val = {'allowPing': {'default': 'true', 'description': 'Allow access to ping', 'value': 'true', 'type': 'boolean'},
                    'enableHttp': {'default': 'true', 'description': 'Enable HTTP', 'value': 'false', 'type': 'boolean'}}
        payload = {'updates': [{'json_properties': [{'path': ['enableHttp', 'value'], 'column': 'value', 'value': 'false'}],
                                'return': ['key', 'description', {'format': 'YYYY-MM-DD HH24:MI:SS.MS', 'column': 'ts'}, 'value'],
                                'where': {'value': 'rest_api', 'column': 'key', 'condition': '='}}]}
        audit_details = {'items': {'enableHttp': {'oldValue': 'true', 'newValue': 'false'}}, 'category': category_name}
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv1 = await async_mock(cat_info)
            _rv2 = await async_mock(update_result)
            _rv3 = await async_mock(read_val)
            _rv4 = await async_mock(None)
        else:
            _rv1 = asyncio.ensure_future(async_mock(cat_info))
            _rv2 = asyncio.ensure_future(async_mock(update_result))
            _rv3 = asyncio.ensure_future(async_mock(read_val))
            _rv4 = asyncio.ensure_future(async_mock(None))        

        with patch.object(c_mgr, 'get_category_all_items', return_value=_rv1) as patch_get_all_items:
            with patch.object(c_mgr._storage, 'update_tbl', return_value=_rv2) as patch_update:
                with patch.object(c_mgr, '_read_category_val', return_value=_rv3) as patch_read_val:
                    with patch.object(AuditLogger, '__init__', return_value=None):
                        with patch.object(AuditLogger, 'information', return_value=_rv4):
                            with patch.object(ConfigurationManager, '_run_callbacks', return_value=_rv4):
                                await c_mgr.update_configuration_item_bulk(category_name, config_item_list)
                patch_read_val.assert_called_once_with(category_name)
            assert 1 == patch_update.call_count
        patch_get_all_items.assert_called_once_with(category_name)

    @pytest.mark.parametrize("config_item_list", [
        {'info': "2"},
        {'info': "2", "info1": "9"},
        {'info1': "2", "info": "9"}
    ])
    async def test_update_configuration_item_bulk_with_rule_optional_attribute(self, config_item_list,
                                                                               category_name='testcat'):
        async def async_mock(return_value):
            return return_value

        cat_info = {'info': {'rule': 'value*3==9', 'default': '3', 'description': 'Test', 'value': '3',
                             'type': 'integer'}, 'info1': {'default': '3', 'description': 'Test', 'value': '3',
                                                           'type': 'integer'}}
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)

        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(cat_info)
        else:
            _rv = asyncio.ensure_future(async_mock(cat_info))

        with patch.object(c_mgr, 'get_category_all_items', return_value=_rv) as patch_get_all_items:
            with patch.object(_logger, 'exception') as patch_log_exc:
                with pytest.raises(Exception) as exc_info:
                    await c_mgr.update_configuration_item_bulk(category_name, config_item_list)
                assert exc_info.type is ValueError
                assert 'The value of info is not valid, please supply a valid value' == str(exc_info.value)
            assert 1 == patch_log_exc.call_count
        patch_get_all_items.assert_called_once_with(category_name)

    @pytest.mark.parametrize("list_type, payload, exc_type, exc_msg", [
        ('list', {ITEM_NAME: "{}"}, TypeError, 'New value should be passed in list'),
        ('list', {ITEM_NAME: "[]"}, ValueError, 'enum value cannot be empty'),
        ('list', {ITEM_NAME: "[\"1\"]"}, ValueError, 'For 1, new value does not exist in options enum'),
        ('kvlist', {ITEM_NAME: "[]"}, TypeError, 'New value should be in KV pair format'),
        ('kvlist', {ITEM_NAME: "{\"key1\":\"\"}"}, ValueError, 'For key1, enum value cannot be empty'),
        ('kvlist', {ITEM_NAME: "{\"key1\":\"b1\",\"key2\":\"b\"}"}, ValueError,
         'For key1, new value does not exist in options enum')
    ])
    async def test_bad_update_configuration_item_bulk_with_list_type(self, list_type, payload, exc_type, exc_msg):
        category_name = 'testcat'
        if list_type == 'kvlist':
            cat_info = {ITEM_NAME: {'type': 'kvlist', 'default': '{"key1": "a", "key2": "b"}', 'items': 'enumeration',
                                    'options': ['b', 'a'], 'listSize': '2', 'description': 'test desc',
                                    'value': '{"key1":"a1", "key2":"b"}'}}
        else:
            cat_info = {ITEM_NAME: {'type': 'list', 'default': '[\"999\"]', 'items': 'enumeration',
                                    'options': ['13', '999'], 'listSize': '2', 'description': 'test desc',
                                    'value': '[\"13\"]'}}

        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        _rv = await async_mock(cat_info) if sys.version_info.major == 3 and sys.version_info.minor >= 8 else (
            asyncio.ensure_future(async_mock(cat_info)))

        with patch.object(c_mgr, 'get_category_all_items', return_value=_rv) as patch_get_all_items:
            with patch.object(_logger, 'exception') as patch_log_exc:
                with pytest.raises(Exception) as exc_info:
                    await c_mgr.update_configuration_item_bulk(category_name, payload)
                assert exc_type == exc_info.type
                assert exc_msg == str(exc_info.value)
            assert 1 == patch_log_exc.call_count
        patch_get_all_items.assert_called_once_with(category_name)

    async def test_set_optional_value_entry_good_update(self, reset_singleton):
        async def async_mock(return_value):
            return return_value

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        category_name = 'catname'
        item_name = 'itemname'
        new_value_entry = '25'
        optional_key_name = 'maximum'
        storage_value_entry = {'readonly': 'true', 'type': 'string', 'order': '4', 'description': 'Test Optional', 'minimum': '2', 'value': '13', 'maximum': '20', 'default': '13'}
        new_storage_value_entry = {'readonly': 'true', 'type': 'string', 'order': '4', 'description': 'Test Optional', 'minimum': '2', 'value': '13', 'maximum': new_value_entry, 'default': '13'}
        payload = {"return": ["key", "description", {"column": "ts", "format": "YYYY-MM-DD HH24:MI:SS.MS"}, "value"], "json_properties": [{"column": "value", "path": [item_name, optional_key_name], "value": new_value_entry}], "where": {"column": "key", "condition": "=", "value": category_name}}
        update_result = {"response": "updated", "rows_affected": 1}
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _se = await async_mock(storage_value_entry)
            _rv = await async_mock(update_result)
        else:
            _se = asyncio.ensure_future(async_mock(storage_value_entry))
            _rv = asyncio.ensure_future(async_mock(update_result))        
        
        with patch.object(ConfigurationManager, '_read_item_val', side_effect=[_se, _se]) as readpatch:
            with patch.object(c_mgr._storage, 'update_tbl', return_value=_rv) as patch_update:
                await c_mgr.set_optional_value_entry(category_name, item_name, optional_key_name, new_value_entry)
            args, kwargs = patch_update.call_args
            assert 'configuration' == args[0]
            assert payload == json.loads(args[1])
        assert 2 == readpatch.call_count
        calls = readpatch.call_args_list
        args, kwargs = calls[0]
        assert category_name == args[0]
        assert item_name == args[1]
        args, kwargs = calls[1]
        assert category_name == args[0]
        assert item_name == args[1]

    @pytest.mark.parametrize("_type, optional_key_name, new_value_entry, exc_msg", [
        (int, 'maximum', '1', 'Maximum value should be greater than equal to Minimum value'),
        (int, 'maximum', '00100', 'Maximum value should be greater than equal to Minimum value'),
        (float, 'maximum', '11.2', 'Maximum value should be greater than equal to Minimum value'),
        (int, 'minimum', '30', 'Minimum value should be less than equal to Maximum value'),
        (float, 'minimum', '50.0', 'Minimum value should be less than equal to Maximum value'),
        (None, 'readonly', '1',
         "For catname category, entry value must be boolean for optional item name readonly; got <class 'str'>"),
        (None, 'deprecated', '1',
         "For catname category, entry value must be boolean for optional item name deprecated; got <class 'str'>"),
        (None, 'rule', 2, "For catname category, entry value must be string for optional item rule; got <class 'int'>"),
        (None, 'displayName', 123,
         "For catname category, entry value must be string for optional item displayName; got <class 'int'>"),
        (None, 'length', '1a',
         "For catname category, entry value must be an integer for optional item length; got <class 'str'>"),
        (None, 'maximum', 'blah',
         "For catname category, entry value must be an integer or float for optional item maximum; got <class 'str'>"),
        (None, 'validity', 12,
         "For catname category, entry value must be string for optional item validity; got <class 'int'>"),
        (None, 'mandatory', '1',
         "For catname category, entry value must be boolean for optional item name mandatory; got <class 'str'>"),
        (None, 'group', 5,
         "For catname category, entry value must be string for optional item group; got <class 'int'>"),
        (None, 'group', True,
         "For catname category, entry value must be string for optional item group; got <class 'bool'>"),
        (None, 'properties', {"key": "Bot"}, 'For catname category, optional item name properties cannot be updated.')
    ])
    async def test_set_optional_value_entry_bad_update(self, reset_singleton, _type, optional_key_name,
                                                       new_value_entry, exc_msg):
        async def async_mock(return_value):
            return return_value

        minimum = '2'
        maximum = '20'
        if _type is not None:
            if isinstance(1.1, _type):
                minimum = '12.5'
                maximum = '40.3'

        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        category_name = 'catname'
        item_name = 'itemname'
        storage_value_entry = {'length': '255', 'displayName': category_name, 'rule': 'value * 3 == 6',
                               'deprecated': 'false', 'readonly': 'true', 'type': 'string', 'order': '4',
                               'description': 'Test Optional', 'minimum': minimum, 'value': '13', 'maximum': maximum,
                               'default': '13', 'validity': 'field X is set', 'mandatory': 'false', 'group': 'Security',
                               'properties': {"key": "model"}}
        
        # Changed in version 3.8: patch() now returns an AsyncMock if the target is an async function.
        if sys.version_info.major == 3 and sys.version_info.minor >= 8:
            _rv = await async_mock(storage_value_entry)
        else:
            _rv = asyncio.ensure_future(async_mock(storage_value_entry))        
        
        with patch.object(_logger, "exception") as log_exc:
            with patch.object(ConfigurationManager, '_read_item_val', return_value=_rv) as readpatch:
                with pytest.raises(Exception) as excinfo:
                    await c_mgr.set_optional_value_entry(category_name, item_name, optional_key_name, new_value_entry)

                assert excinfo.type is ValueError
                assert exc_msg == str(excinfo.value)
            readpatch.assert_called_once_with(category_name, item_name)
        assert 1 == log_exc.call_count
        log_exc.assert_called_once_with('Unable to set optional %s entry based on category_name %s and item_name %s and value_item_entry %s', optional_key_name, 'catname', 'itemname', new_value_entry)

    @pytest.mark.parametrize("new_value_entry, storage_value_entry, exc_msg, exc_type", [
        ("Fledge", {'default': 'FOG', 'length': '3', 'displayName': 'Length Test', 'value': 'fog', 'type': 'string',
                    'description': 'Test value '},
         'For config item {} you cannot set the new value, beyond the length 3', TypeError),
        ("0", {'order': '4', 'default': '10', 'minimum': '10', 'maximum': '19', 'displayName': 'RangeMin Test',
               'value': '15', 'type': 'integer', 'description': 'Test value'},
         'For config item {} you cannot set the new value, beyond the range (10,19)', TypeError),
        ("20", {'order': '4', 'default': '10', 'minimum': '10', 'maximum': '19', 'displayName': 'RangeMax Test',
                'value': '19', 'type': 'integer', 'description': 'Test value'},
         'For config item {} you cannot set the new value, beyond the range (10,19)', TypeError),
        ("1", {'order': '5', 'default': '2', 'minimum': '2', 'displayName': 'MIN', 'value': '10', 'type': 'integer',
               'description': 'Test value '}, 'For config item {} you cannot set the new value, below 2', TypeError),
        ("11", {'default': '10', 'maximum': '10', 'displayName': 'MAX', 'value': '10', 'type': 'integer',
                'description': 'Test value'}, 'For config item {} you cannot set the new value, above 10', TypeError),
        ("19.0", {'default': '19.3', 'minimum': '19.1', 'maximum': '19.5', 'displayName': 'RangeMin Test',
                  'value': '19.1', 'type': 'float', 'description': 'Test val'},
         'For config item {} you cannot set the new value, beyond the range (19.1,19.5)', TypeError),
        ("19.6", {'default': '19.4', 'minimum': '19.1', 'maximum': '19.5', 'displayName': 'RangeMax Test',
                  'value': '19.5', 'type': 'float', 'description': 'Test val'},
         'For config item {} you cannot set the new value, beyond the range (19.1,19.5)', TypeError),
        ("20", {'order': '8', 'default': '10.1', 'maximum': '19.8', 'displayName': 'MAX Test', 'value': '10.1',
                'type': 'float', 'description': 'Test value'},
         'For config item {} you cannot set the new value, above 19.8', TypeError),
        ("0.7", {'order': '9', 'default': '0.9', 'minimum': '0.8', 'displayName': 'MIN Test', 'value': '0.9',
                 'type': 'float', 'description': 'Test value'},
         'For config item {} you cannot set the new value, below 0.8', TypeError),
        ("", {'description': 'Simple list', 'type': 'list', 'default': '[\"1\", \"1\"]', 'order': '2',
                'items': 'integer', 'listSize': '2', 'value': '[\"1\", \"2\"]'},
         "For config item {} value should be passed array list in string format", TypeError),
        ("[\"5\", \"7\", \"9\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"1\", \"3\"]',
                                   'order': '2', 'items': 'integer', 'listSize': '2', 'value': '[\"5\", \"7\"]'},
         "For config item {} value array list size limit to 2", TypeError),
        ("", {'description': 'Simple list', 'type': 'list', 'default': '[\"foo\"]', 'order': '2',
                'items': 'string', 'listSize': '1', 'value': '[\"bar\"]'},
         "For config item {} value should be passed array list in string format", TypeError),
        ("", {'description': 'Simple list', 'type': 'list', 'default': '[\"foo\"]', 'order': '2',
                'items': 'string', 'listSize': '1', 'value': '[\"bar\"]'},
         "For config item {} value should be passed array list in string format", TypeError),
        ("[\"foo\", \"bar\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"foo\"]', 'order': '2',
                                'items': 'string', 'listSize': '1', 'value': '[\"bar\"]'},
         "For config item {} value array list size limit to 1", TypeError),
        ("[\"1.4\", \".03\", \"50.67\", \"13.13\"]",
         {'description': 'Simple list', 'type': 'list', 'default': '[\"1.4\", \".03\", \"50.67\"]', 'order': '2',
          'items': 'float', 'listSize': '3', 'value': '[\"1.4\", \".03\", \"50.67\"]'},
         "For config item {} value array list size limit to 3", TypeError),
        ("[\"10\", \"10\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"1\", \"2\"]', 'order': '2',
                'items': 'integer', 'value': '[\"3\", \"4\"]'}, "For config item {} elements are not unique", ValueError),
        ("[\"foo\", \"foo\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"a\", \"c\"]', 'order': '2',
                              'items': 'string', 'value': '[\"abc\", \"def\"]'},
         "For config item {} elements are not unique", ValueError),
        ("[\".002\", \".002\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"1.2\", \"1.4\"]',
                                  'order': '2', 'items': 'float', 'value': '[\"5.67\", \"12.0\"]'},
         "For config item {} elements are not unique", ValueError),
        ("[\"10\", \"foo\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"1\", \"2\"]', 'order': '2',
                              'items': 'integer', 'value': '[\"3\", \"4\"]'},
         "For config item {} all elements should be of same integer type", ValueError),
        ("[\"foo\", 1]", {'description': 'Simple list', 'type': 'list', 'default': '[\"a\", \"c\"]', 'order': '2',
                                'items': 'string', 'value': '[\"abc\", \"def\"]'},
         "For config item {} all elements should be of same string type", ValueError),
        ("[\"1\", \"2\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"1.2\", \"1.4\"]',
                                  'order': '2', 'items': 'float', 'value': '[\"5.67\", \"12.0\"]'},
         "For config item {} all elements should be of same float type", ValueError),
        ("[\"100\", \"2\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"34\", \"48\"]', 'order': '2',
                              'items': 'integer', 'listSize': '2', 'value': '[\"34\", \"48\"]', 'minimum': '20'},
         "For config item {} you cannot set the new value, below 20", ValueError),
        ("[\"50\", \"49\", \"51\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"34\", \"48\"]',
                                       'order': '2', 'items': 'integer', 'listSize': '3',
                                       'value': '[\"34\", \"48\"]', 'maximum': '50'},
         "For config item {} you cannot set the new value, above 50", ValueError),
        ("[\"50\", \"49\", \"46\"]", {'description': 'Simple list', 'type': 'list', 'default':
            '[\"50\", \"48\", \"49\"]', 'order': '2', 'items': 'integer', 'listSize': '3',
                                      'value': '[\"47\", \"48\", \"49\"]', 'maximum': '50', 'minimum': '47'},
         "For config item {} you cannot set the new value, beyond the range (47,50)", ValueError),
        ("[\"50\", \"49\", \"51\"]", {'description': 'Simple list', 'type': 'list', 'default':
            '[\"50\", \"48\", \"49\"]', 'order': '2', 'items': 'integer', 'listSize': '3',
                                      'value': '[\"47\", \"48\", \"49\"]', 'maximum': '50', 'minimum': '47'},
         "For config item {} you cannot set the new value, beyond the range (47,50)", ValueError),
        ("[\"foo\", \"bars\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"a1\", \"c1\"]',
                                 'order': '2', 'items': 'string', 'value': '[\"ab\", \"de\"]', 'listSize': '2',
                                 'length': '3'},
         "For config item {} you cannot set the new value, beyond the length 3", ValueError),
        ("[\"2.6\", \"1.002\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"5.2\", \"2.5\"]',
                                  'order': '2', 'items': 'float', 'value': '[\"5.67\", \"2.5\"]', 'minimum': '2.5',
                                  'listSize': '2'}, "For config item {} you cannot set the new value, below 2.5",
         ValueError),
        ("[\"2.6\", \"1.002\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"2.2\", \"2.5\"]',
                                  'order': '2', 'items': 'float', 'value': '[\"1.67\", \"2.5\"]', 'maximum': '2.5',
                                  'listSize': '2'}, "For config item {} you cannot set the new value, above 2.5",
         ValueError),
        ("[\"2.6\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"2.2\"]', 'order': '2',
                       'items': 'float', 'value': '[\"2.5\"]', 'listSize': '1', 'minimum': '2', 'maximum': '2.5'},
         "For config item {} you cannot set the new value, beyond the range (2,2.5)", ValueError),
        ("[\"1.999\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"2.2\"]', 'order': '2',
                       'items': 'float', 'value': '[\"2.5\"]', 'listSize': '1', 'minimum': '2', 'maximum': '2.5'},
         "For config item {} you cannot set the new value, beyond the range (2,2.5)", ValueError),
        ("", {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"val\"}', 'order': '2',
              'items': 'integer', 'listSize': '1', 'value': '{\"key\": \"val\"}'},
         "For config item {} value should be passed KV pair list in string format", TypeError),
        ("{\"key\": \"1\", \"key2\": \"2\"}",
         {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"1\"}', 'order': '2',
          'items': 'integer', 'listSize': '1', 'value': '{\"key\": \"2\"}'},
         "For config item {} value KV pair list size limit to 1", TypeError),
        ("", {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"val\"}', 'order': '2',
              'items': 'string', 'listSize': '1', 'value': '{\"key\": \"val\"}'},
         "For config item {} value should be passed KV pair list in string format", TypeError),
        ("", {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"val\"}', 'order': '2',
              'items': 'string', 'listSize': '1', 'value': '[\"bar\"]'},
         "For config item {} value should be passed KV pair list in string format", TypeError),
        ("{\"key\": \"val\", \"key2\": \"val2\"}",
         {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"val\"}', 'order': '2',
          'items': 'string', 'listSize': '1', 'value': '{\"key\": \"val\"}'},
         "For config item {} value KV pair list size limit to 1", TypeError),
        ("{\"key\": \"1.2\", \"key2\": \"0.9\", \"key3\": \"444.12\"}",
         {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"1.2\", \"key2\": \"0.9\"}',
          'order': '2', 'items': 'float', 'listSize': '2', 'value': '{\"key\": \"1.2\", \"key2\": \"0.9\"}'},
         "For config item {} value KV pair list size limit to 2", TypeError),
        ("{\"key\": \"1.2\", \"key\": \"1.23\"}", {'description': 'Simple list', 'type': 'kvlist', 'default': '{\"key\": \"11.12\"}',
                                  'order': '2', 'items': 'float', 'value': '{\"key\": \"1.4\"}'},
         "For config item {} duplicate KV pair found", TypeError),
        ("{\"key\": \"val\"}", {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"1\"}',
                               'items': 'integer', 'value': '{\"key\": \"13\"}'},
         "For config item {} all elements should be of same integer type", ValueError),
        ("{\"key\": 1}", {'description': 'expression', 'type': 'kvlist', 'default': '{\"a\": \"c\"}', 'order': '2',
                          'items': 'string', 'value': '{\"abc\", \"def\"}'},
         "For config item {} all elements should be of same string type", ValueError),
        ("{\"key\": \"2\"}", {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"1.4\"}',
                            'order': '2', 'items': 'float', 'value': '{\"key\": \"12.0\"}'},
         "For config item {} all elements should be of same float type", ValueError),
        ("{\"key\": \"2\"}", {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"48\"}',
                              'items': 'integer', 'listSize': '1', 'value': '{\"key\": \"48\"}', 'minimum': '20'},
         "For config item {} you cannot set the new value, below 20", ValueError),
        ("{\"key\": \"100\"}", {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"48\"}',
                                'items': 'integer', 'listSize': '1', 'value': '{\"key\": \"48\"}', 'maximum': '50'},
         "For config item {} you cannot set the new value, above 50", ValueError),
        ("{\"key\": \"46\"}", {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"50\"}',
                               'items': 'integer', 'listSize': '1', 'value': '{\"key\": \"48\"}', 'maximum': '50',
                               'minimum': '47'}, "For config item {} you cannot set the new value, beyond the "
                                                 "range (47,50)", ValueError),
        ("{\"key\": \"100\"}", {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"48\"}',
                                'items': 'integer', 'listSize': '1', 'value': '{\"key\": \"48\"}', 'maximum': '50',
                                'minimum': '47'},
         "For config item {} you cannot set the new value, beyond the range (47,50)", ValueError),
        ("{\"foo\": \"bars\"}", {'description': 'expression', 'type': 'kvlist', 'default': '{\"a1\": \"c1\"}',
                                 'items': 'string', 'value': '[\"ab\", \"de\"]', 'listSize': '1', 'length': '3'},
         "For config item {} you cannot set the new value, beyond the length 3", ValueError),
        ("{\"key\": \"1.002\", \"key2\": \"2.6\"}", {'description': 'expression', 'type': 'kvlist',
                                                     'default': '{\"key\", \"2.5\"}', 'items': 'float',
                                                     'value': '{\"key\", \"2.5\"}', 'minimum': '2.5', 'listSize': '2'},
         "For config item {} you cannot set the new value, below 2.5", ValueError),
        ("{\"key\": \"2.6\"}", {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"2.5\"}',
                                  'items': 'float', 'value': '{\"key\": \"2.5\"}', 'maximum': '2.5',
                                  'listSize': '1'}, "For config item {} you cannot set the new value, above 2.5",
         ValueError),
        ("{\"key\": \"2.6\"}", {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"2.2\"}',
                                'items': 'float', 'value': '{\"key\": \"2.5\"}', 'listSize': '1', 'minimum': '2',
                                'maximum': '2.5'},
         "For config item {} you cannot set the new value, beyond the range (2,2.5)", ValueError),
        ("{\"key\": \"1.999\"}", {'description': 'expression', 'type': 'kvlist', 'default': '{\"key\": \"2.2\"}',
                         'items': 'float', 'value': '{\"key\": \"2.5\"}', 'listSize': '1', 'minimum': '2',
                                  'maximum': '2.5'},
         "For config item {} you cannot set the new value, beyond the range (2,2.5)", ValueError)
    ])
    def test_bad__validate_value_per_optional_attribute(self, new_value_entry, storage_value_entry, exc_msg, exc_type):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        with pytest.raises(Exception) as exc_info:
            c_mgr._validate_value_per_optional_attribute(ITEM_NAME, storage_value_entry, new_value_entry)
        assert exc_info.type is exc_type
        msg = exc_msg.format(ITEM_NAME)
        assert msg == str(exc_info.value)

    @pytest.mark.parametrize("new_value_entry, storage_value_entry", [
        ("Fledge", {'default': 'FOG', 'length': '7', 'displayName': 'Length Test', 'value': 'fledge',
                    'type': 'string', 'description': 'Test value '}),
        ("2", {'order': '5', 'default': '10', 'minimum': '2', 'displayName': 'MIN', 'value': '10', 'type': 'integer',
               'description': 'Test value '}),
        ("19.1", {'default': '19.4', 'minimum': '19.1', 'maximum': '19.5', 'displayName': 'RangeMin Test',
                  'value': '19.5', 'type': 'float', 'description': 'Test val'}),
        ("19.5", {'default': '19.4', 'minimum': '19.1', 'maximum': '19.5', 'displayName': 'RangeMax Test',
                  'value': '19.5', 'type': 'float', 'description': 'Test val'}),
        ("19.2", {'default': '19.4', 'minimum': '19.1', 'maximum': '19.5', 'displayName': 'Range Test',
                  'value': '19.5', 'type': 'float', 'description': 'Test val'}),
        ("10", {'order': '4', 'default': '10', 'minimum': '10', 'maximum': '19', 'displayName': 'RangeMin Test',
                'value': '15', 'type': 'integer', 'description': 'Test value'}),
        ("19", {'order': '4', 'default': '10', 'minimum': '10', 'maximum': '19', 'displayName': 'RangeMax Test',
                'value': '15', 'type': 'integer', 'description': 'Test value'}),
        ("15", {'order': '4', 'default': '10', 'minimum': '10', 'maximum': '19', 'displayName': 'Range Test',
                'value': '15', 'type': 'integer', 'description': 'Test value'}),
        ("[]", {'description': 'Simple list', 'type': 'list', 'default': '[\"1\", \"2\"]', 'order': '2',
                'items': 'integer', 'value': '[\"3\", \"4\"]'}),
        ("[\"10\", \"20\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"1\", \"2\"]', 'order': '2',
                              'items': 'integer', 'value': '[\"3\", \"4\"]'}),
        ("[\"foo\", \"bar\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"a\", \"c\"]', 'order': '2',
                                'items': 'string', 'value': '[\"abc\", \"def\"]'}),
        ("[\".002\", \"1.002\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"1.2\", \"1.4\"]',
                                  'order': '2', 'items': 'float', 'value': '[\"5.67\", \"12.0\"]'}),
        ("[\"10\", \"20\", \"30\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"1\", \"2\"]',
                                      'order': '2', 'items': 'integer', 'listSize': "3", 'value': '[\"3\", \"4\"]'}),
        ("[\"new string\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"a\", \"c\"]', 'order': '2',
                                'items': 'string', 'listSize': "1", 'value': '[\"abc\", \"def\"]'}),
        ("[\"6.523e-07\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"1.2\", \"1.4\"]',
                                   'order': '2', 'items': 'float', 'listSize': "1", 'value': '[\"5.67\", \"12.0\"]'}),
        ("[]", {'description': 'Simple list', 'type': 'list', 'default': '[\"1\", \"2\"]',
                                      'order': '2', 'items': 'integer', 'listSize': "0", 'value': '[\"3\", \"4\"]'}),
        ("[]", {'description': 'Simple list', 'type': 'list', 'default': '[\"a\", \"c\"]', 'order': '2',
                              'items': 'string', 'listSize': "0", 'value': '[\"abc\", \"def\"]'}),
        ("[]", {'description': 'Simple list', 'type': 'list', 'default': '[\"1.2\", \"1.4\"]',
                             'order': '2', 'items': 'float', 'listSize': "0", 'value': '[\"5.67\", \"12.0\"]'}),
        ("[]", {'description': 'Simple list', 'type': 'list', 'default': '[\"a\", \"c\"]', 'order': '2',
                'items': 'string', 'listSize': "1", 'value': '[\"abc\", \"def\"]'}),
        ("[\"100\", \"20\"]", {'description': 'SL', 'type': 'list', 'default': '[\"34\", \"48\"]', 'order': '2',
                               'items': 'integer', 'listSize': '2', 'value': '[\"34\", \"48\"]', 'minimum': '20'}),
        ("[\"50\", \"49\", \"0\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"34\", \"48\"]',
                                      'order': '2', 'items': 'integer', 'listSize': '3',
                                      'value': '[\"34\", \"48\"]', 'maximum': '50'}),
        ("[\"50\", \"49\", \"47\"]", {'description': 'Simple list', 'type': 'list', 'default':
            '[\"50\", \"48\", \"49\"]', 'order': '2', 'items': 'integer', 'listSize': '3',
                                      'value': '[\"47\", \"48\", \"49\"]', 'maximum': '50', 'minimum': '47'}),
        ("[\"50\", \"49\", \"48\"]", {'description': 'Simple list', 'type': 'list', 'default':
            '[\"50\", \"48\", \"49\"]', 'order': '2', 'items': 'integer', 'listSize': '3',
                                      'value': '[\"47\", \"48\", \"49\"]', 'maximum': '50', 'minimum': '47'}),
        ("[\"foo\", \"bar\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"a1\", \"c1\"]',
                                 'order': '2', 'items': 'string', 'value': '[\"ab\", \"de\"]', 'listSize': '2',
                                 'length': '3'}),
        ("[\"2.6\", \"13.002\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"5.2\", \"2.5\"]',
                                  'order': '2', 'items': 'float', 'value': '[\"5.67\", \"2.5\"]', 'minimum': '2.5',
                                  'listSize': '2'}),
        ("[\"2.4\", \"1.002\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"2.2\", \"2.5\"]',
                                  'order': '2', 'items': 'float', 'value': '[\"1.67\", \"2.5\"]', 'maximum': '2.5',
                                  'listSize': '2'}),
        ("[\"2.0\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"2.2\"]', 'order': '2',
                       'items': 'float', 'value': '[\"2.5\"]', 'listSize': '1', 'minimum': '2', 'maximum': '2.5'}),
        ("[\"2.5\"]", {'description': 'Simple list', 'type': 'list', 'default': '[\"2.2\"]', 'order': '2',
                         'items': 'float', 'value': '[\"2.5\"]', 'listSize': '1', 'minimum': '2', 'maximum': '2.5'}),
        ("{\"key\": \"bar\"}",
         {'description': 'A list of expressions and values', 'type': 'kvlist', 'default': '{\"key\": \"c\"}',
          'order': '2',
          'items': 'string', 'value': '{\"key\": \"def\"}'}),
        ("{\"key\": \"1.002\"}",
         {'description': 'A list of expressions and values', 'type': 'kvlist', 'default': '{\"key\": \"1.4\"}',
          'order': '2', 'items': 'float', 'value': '{\"key\": \"12.0\"}'}),
        ("{\"key\": \"10\", \"key1\": \"20\", \"key2\": \"30\"}",
         {'description': 'A list of expressions and values', 'type': 'kvlist',
          'default': '{\"key\": \"10\", \"key1\": \"20\", \"key2\": \"30\"}',
          'order': '2', 'items': 'integer', 'listSize': "3",
          'value': '{\"key\": \"1\", \"key1\": \"2\", \"key2\": \"3\"}'}),
        ("{\"key\": \"new string\"}",
         {'description': 'A list of expressions and values', 'type': 'kvlist', 'default': '{\"key\": \"c\"}',
          'order': '2',
          'items': 'string', 'listSize': "1", 'value': '{\"key\": \"def\"}'}),
        ("{\"key\": \"6.523e-07\"}",
         {'description': 'A list of expressions and values', 'type': 'kvlist', 'default': '{\"key\": \"1.4\"}',
          'order': '2', 'items': 'float', 'listSize': "1", 'value': '{\"key\": \"12.0\"}'}),
        ("{}", {'description': 'A list of expressions and values', 'type': 'kvlist', 'default': '{\"1\": \"2\"}',
                'order': '2', 'items': 'integer', 'listSize': "0", 'value': '{\"3\": \"4\"}'}),
        ("{}", {'description': 'A list of expressions and values', 'type': 'kvlist', 'default': '{\"a\": \"c\"}',
                'order': '2',
                'items': 'string', 'listSize': "0", 'value': '{\"abc\": \"def\"}'}),
        ("{}", {'description': 'A list of expressions and values', 'type': 'kvlist', 'default': '{\"key\": \"1.4\"}',
                'order': '2', 'items': 'float', 'listSize': "0", 'value': '{\"key\": \"12.0\"}'}),
        ("{}", {'description': 'A list of expressions and values', 'type': 'kvlist', 'default': '{\"1\": \"2\"}',
                'order': '2', 'items': 'integer', 'listSize': "1", 'value': '{\"3\": \"4\"}'}),
        ("{\"key\": \"100\", \"key2\": \"20\"}",
         {'description': 'SL', 'type': 'kvlist', 'default': '{\"key\": \"100\", \"key2\": \"48\"}', 'order': '2',
          'items': 'integer', 'listSize': '2', 'value': '{\"key\": \"34\", \"key2\": \"20\"}', 'minimum': '20'}),
        ("{\"key\": \"50\", \"key2\": \"0\", \"key3\": \"49\"}",
         {'description': 'A list of expressions and values', 'type': 'kvlist',
          'default': '{\"key\": \"47\", \"key2\": \"48\", \"key3\": \"49\"}',
          'order': '2', 'items': 'integer', 'listSize': '3',
          'value': '{\"key\": \"47\", \"key2\": \"48\", \"key3\": \"49\"}', 'maximum': '50'}),
        ("{\"key\": \"50\", \"key2\": \"48\", \"key3\": \"49\"}",
         {'description': 'A list of expressions and values', 'type': 'kvlist', 'default':
             '{\"key\": \"50\", \"key2\": \"48\", \"key3\": \"49\"}', 'order': '2', 'items': 'integer', 'listSize': '3',
          'value': '{\"key\": \"47\", \"key2\": \"48\", \"key3\": \"49\"}', 'maximum': '50', 'minimum': '47'}),
        ("{\"key\": \"50\", \"key2\": \"48\", \"key3\": \"49\"}",
         {'description': 'A list of expressions and values', 'type': 'kvlist', 'default':
             '{\"key\": \"47\", \"key2\": \"48\", \"key3\": \"49\"}', 'order': '2', 'items': 'integer', 'listSize': '3',
          'value': '{\"key\": \"47\", \"key2\": \"48\", \"key3\": \"49\"}', 'maximum': '50', 'minimum': '47'}),
        ("{\"key\": \"foo\", \"key2\": \"bar\"}", {'description': 'A list of expressions and values', 'type': 'kvlist',
                                                   'default': '{\"key\": \"a1\", \"key2\": \"c1\"}',
                                                   'order': '2', 'items': 'string',
                                                   'value': '{\"key\": \"ab\", \"key2\": \"de\"}', 'listSize': '2',
                                                   'length': '3'}),
        ("{\"key\": \"2.6\", \"key2\": \"13.002\"}",
         {'description': 'A list of expressions and values', 'type': 'kvlist',
          'default': '{\"key\": \"5.2\", \"key2\": \"2.5\"}',
          'order': '2', 'items': 'float', 'value': '{\"key\": \"5.67\", \"key2\": \"2.5\"}', 'minimum': '2.5',
          'listSize': '2'}),
        ("{\"key\": \"2.4\", \"key2\": \"1.002\"}",
         {'description': 'A list of expressions and values', 'type': 'kvlist',
          'default': '{\"key\": \"2.2\", \"key2\": \"2.5\"}', 'order': '2', 'items': 'float',
          'value': '{\"key\": \"1.67\", \"key2\": \"2.5\"}', 'maximum': '2.5', 'listSize': '2'}),
        ("{\"key\": \"2.0\"}", {'description': 'A list of expressions and values', 'type': 'kvlist',
                                'default': '{\"key\": \"2.2\"}', 'order': '2', 'items': 'float', 'value': '{\"2.5\"}',
                                'listSize': '1', 'minimum': '2', 'maximum': '2.5'}),
        ("{\"key\": \"2.5\"}", {'description': 'A list of expressions and values', 'type': 'kvlist',
                                'default': '{\"key\": \"2.2\"}', 'order': '2', 'items': 'float', 'value': '{\"2.5\"}',
                                'listSize': '1', 'minimum': '2', 'maximum': '2.5'})
    ])
    def test_good__validate_value_per_optional_attribute(self, new_value_entry, storage_value_entry):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        raised = False
        try:
            c_mgr._validate_value_per_optional_attribute(ITEM_NAME, storage_value_entry, new_value_entry)
        except Exception:
            raised = True
        assert raised is False

    async def test__ignore_unrecognized_key_in_config_items(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        entry_name = "test_entry"
        test_config = {
            ITEM_NAME: {
                "description": "Test with entry_name",
                "type": "string",
                "default": "test_default_value",
                entry_name: "some_value"
            }
        }
        with patch.object(_logger, 'warning') as log_warn:
            await c_mgr._validate_category_val(CAT_NAME, test_config)
        assert 1 == log_warn.call_count
        log_warn.assert_called_once_with('For {} category, DISCARDING unrecognized entry name {} for item name {}'.
                                         format(CAT_NAME, entry_name, ITEM_NAME))

    async def test__ignore_unrecognized_key_in_config_items_without_set_value_val_from_default_val(self):
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        c_mgr = ConfigurationManager(storage_client_mock)
        entry_name = "blah"
        test_config = {
            ITEM_NAME: {
                "description": "test description val",
                "type": "integer",
                "default": "test default val",
                entry_name: "some_value"
            },
        }
        with patch.object(_logger, 'warning') as log_warn:
            with pytest.raises(ValueError) as excinfo:
                await c_mgr._validate_category_val(category_name=CAT_NAME, category_val=test_config,
                                                   set_value_val_from_default_val=False)
            assert 'For {} category, missing entry name value for item name {}'.format(
                CAT_NAME, ITEM_NAME) == str(excinfo.value)
        assert 1 == log_warn.call_count
        log_warn.assert_called_once_with('For {} category, DISCARDING unrecognized entry name {} for item name {}'.
                                         format(CAT_NAME, entry_name, ITEM_NAME))
