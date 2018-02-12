import asyncio
import pytest
import json
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.configuration_manager import ConfigurationManagerSingleton
from foglamp.common.storage_client.storage_client import StorageClient
from foglamp.common.configuration_manager import _valid_type_strings
from foglamp.common.audit_logger import AuditLogger
from foglamp.common.storage_client.payload_builder import PayloadBuilder

from unittest.mock import MagicMock
from unittest.mock import patch
from unittest.mock import Mock
from unittest.mock import call

__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestConfigurationManager():
    @pytest.fixture()
    def reset_singleton(self, scope="module"):
        # executed before each test
        ConfigurationManagerSingleton._shared_state = {}
        yield 
        # executed after each test
        ConfigurationManagerSingleton._shared_state = {}

    def test_constructor_no_storage_client_defined_no_storage_client_passed(self,reset_singleton):
        # first time initializing ConfigurationManager without storage client produces error
        with pytest.raises(TypeError) as excinfo:
            ConfigurationManager()
        assert 'Must be a valid Storage object' in str(excinfo.value)

    def test_constructor_no_storage_client_defined_storage_client_passed(self,reset_singleton):
        # first time initializing ConfigurationManager with storage client works
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        assert hasattr(c, '_storage')
        assert c._storage is storageClientMock
        assert hasattr(c, '_registered_interests')
        

    def test_constructor_storage_client_defined_storage_client_passed(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        # second time initializing ConfigurationManager with new storage client works
        storageClientMock2 = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        c2 = ConfigurationManager(storageClientMock2)
        assert hasattr(c2, '_storage')
        # ignore new storage client
        assert c2._storage is storageClientMock
        assert hasattr(c2, '_registered_interests')
        

    def test_constructor_storage_client_defined_no_storage_client_passed(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        # second time initializing ConfigurationManager without storage client works
        c2 = ConfigurationManager()
        assert hasattr(c2, '_storage')
        assert c2._storage is storageClientMock
        assert hasattr(c2, '_registered_interests')
        

    def test_register_interest_no_category_name(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        with pytest.raises(ValueError) as excinfo:
            c.register_interest(None,'callback')
        assert 'Failed to register interest. category_name cannot be None' in str(excinfo.value)
        

    def test_register_interest_no_callback(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        with pytest.raises(ValueError) as excinfo:
            c.register_interest('name',None)
        assert 'Failed to register interest. callback cannot be None' in str(excinfo.value)
        

    def test_register_interest(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        c.register_interest('name','callback')
        assert 'callback' in c._registered_interests['name']
        

    def test_unregister_interest_no_category_name(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        with pytest.raises(ValueError) as excinfo:
            c.unregister_interest(None,'callback')
        assert 'Failed to unregister interest. category_name cannot be None' in str(excinfo.value)
        

    def test_unregister_interest_no_callback(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        with pytest.raises(ValueError) as excinfo:
            c.unregister_interest('name',None)
        assert 'Failed to unregister interest. callback cannot be None' in str(excinfo.value)
        

    def test_unregister_interest(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        c.register_interest('name','callback')
        c.unregister_interest('name','callback')
        assert len(c._registered_interests) is 0
        

    @pytest.mark.asyncio
    async def test__run_callbacks(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        c.register_interest('name','configuration_manager_callback')
        await c._run_callbacks('name')
        

    @pytest.mark.asyncio
    async def test__run_callbacks_invalid_module(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        c.register_interest('name','invalid')
        with pytest.raises(ImportError) as excinfo:
            await c._run_callbacks('name')
        

    @pytest.mark.asyncio
    async def test__run_callbacks_norun(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        c.register_interest('name','configuration_manager_callback_norun')
        with pytest.raises(AttributeError) as excinfo:
            await c._run_callbacks('name')
        assert 'Callback module configuration_manager_callback_norun does not have method run' in str(excinfo.value)
        

    @pytest.mark.asyncio
    async def test__run_callbacks_nonasync(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        c.register_interest('name','configuration_manager_callback_nonasync')
        with pytest.raises(AttributeError) as excinfo:
            await c._run_callbacks('name')
        assert 'Callback module configuration_manager_callback_nonasync run method must be a coroutine function' in str(excinfo.value)
        

    @pytest.mark.asyncio
    async def test__validate_category_val_valid_config_use_default_val(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config = { 
            "test_item_name": {
                "description": "test description val",
                "type": "string",
                "default": "test default val"
            },
        }
        c_return_value = await c._validate_category_val(category_val=test_config, set_value_val_from_default_val=True)
        assert type(c_return_value) is dict 
        assert len(c_return_value) is 1
        test_item_val = c_return_value.get("test_item_name")
        assert type(test_item_val) is dict
        assert len(test_item_val) is 4
        assert test_item_val.get("description") is "test description val"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val"
        assert test_item_val.get("value") is "test default val"

        # deep copy check to make sure test_config wasn't modified in the method call
        assert test_config is not c_return_value
        assert type(test_config) is dict 
        assert len(test_config) is 1
        test_item_val = test_config.get("test_item_name")
        assert type(test_item_val) is dict
        assert len(test_item_val) is 3
        assert test_item_val.get("description") is "test description val"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val"
        

    @pytest.mark.asyncio
    async def test__validate_category_val_valid_config_use_value_val(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config = { 
            "test_item_name": {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                "value": "test value val"
            },
        }
        c_return_value = await c._validate_category_val(category_val=test_config, set_value_val_from_default_val=False)
        assert type(c_return_value) is dict 
        assert len(c_return_value) is 1
        test_item_val = c_return_value.get("test_item_name")
        assert type(test_item_val) is dict
        assert len(test_item_val) is 4
        assert test_item_val.get("description") is "test description val"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val"
        assert test_item_val.get("value") is "test value val"
        # deep copy check to make sure test_config wasn't modified in the method call
        assert test_config is not c_return_value
        assert type(test_config) is dict 
        assert len(test_config) is 1
        test_item_val = test_config.get("test_item_name")
        assert type(test_item_val) is dict
        assert len(test_item_val) is 4
        assert test_item_val.get("description") is "test description val"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val"
        assert test_item_val.get("value") is "test value val"
        
    
    @pytest.mark.asyncio
    async def test__validate_category_val_config_without_value_use_value_val(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config = { 
            "test_item_name": {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
            },
        }
        with pytest.raises(ValueError) as excinfo:
            c_return_value = await c._validate_category_val(category_val=test_config, set_value_val_from_default_val=False)
        assert 'Missing entry_name value for item_name test_item_name' in str(excinfo.value)
        

    @pytest.mark.asyncio
    async def test__validate_category_val_config_not_dictionary(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config = ()
        with pytest.raises(TypeError) as excinfo:
            c_return_value = await c._validate_category_val(category_val=test_config, set_value_val_from_default_val=False)
        assert 'category_val must be a dictionary' in str(excinfo.value)
        

    @pytest.mark.asyncio
    async def test__validate_category_val_item_name_not_string(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config = { 
            5 : {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
            },
        }
        with pytest.raises(TypeError) as excinfo:
            c_return_value = await c._validate_category_val(category_val=test_config, set_value_val_from_default_val=False)
        assert 'item_name must be a string' in str(excinfo.value)
        

    @pytest.mark.asyncio
    async def test__validate_category_val_item_value_not_dictionary(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config = { 
            "test_item_name" : ()
        }
        with pytest.raises(TypeError) as excinfo:
            c_return_value = await c._validate_category_val(category_val=test_config, set_value_val_from_default_val=False)
        assert 'item_value must be a dict for item_name test_item_name' in str(excinfo.value)
        

    @pytest.mark.asyncio
    async def test__validate_category_val_config_entry_name_not_string(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config = { 
            "test_item_name": {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                5: "bla"
            },
        }
        with pytest.raises(TypeError) as excinfo:
            c_return_value = await c._validate_category_val(category_val=test_config, set_value_val_from_default_val=False)
        assert 'entry_name must be a string for item_name test_item_name' in str(excinfo.value)
        

    @pytest.mark.asyncio
    async def test__validate_category_val_config_entry_val_not_string(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config = { 
            "test_item_name": {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                "something": 5
            },
        }
        with pytest.raises(TypeError) as excinfo:
            c_return_value = await c._validate_category_val(category_val=test_config, set_value_val_from_default_val=False)
        assert 'entry_val must be a string for item_name test_item_name and entry_name something' in str(excinfo.value)
        

    @pytest.mark.asyncio
    async def test__validate_category_val_config_unrecognized_entry_name(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config = { 
            "test_item_name": {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                "unrecognized": "unexpected",
            },
        }
        with pytest.raises(ValueError) as excinfo:
            c_return_value = await c._validate_category_val(category_val=test_config, set_value_val_from_default_val=True)
        assert 'Unrecognized entry_name unrecognized for item_name test_item_name' in str(excinfo.value)
        

    @pytest.mark.parametrize("test_input", _valid_type_strings)
    @pytest.mark.asyncio
    async def test__validate_category_val_valid_type(self,reset_singleton, test_input):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config = { 
            "test_item_name": {
                "description": "test description val",
                "type": test_input,
                "default": "test default val",
            },
        }
        c_return_value = await c._validate_category_val(category_val=test_config, set_value_val_from_default_val=True)
        assert c_return_value["test_item_name"]["type"] == test_input
        

    @pytest.mark.asyncio
    async def test__validate_category_val_invalid_type(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config = { 
            "test_item_name": {
                "description": "test description val",
                "type": "blablabla",
                "default": "test default val",
            },
        }
        with pytest.raises(ValueError) as excinfo:
            c_return_value = await c._validate_category_val(category_val=test_config, set_value_val_from_default_val=True)
        assert 'Invalid entry_val for entry_name "type" for item_name test_item_name. valid: {}'.format(_valid_type_strings) in str(excinfo.value)
        

    @pytest.mark.parametrize("test_input", ["type", "description", "default"])
    @pytest.mark.asyncio
    async def test__validate_category_val_missing_entry(self,reset_singleton, test_input):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config = { 
            "test_item_name": {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
            },
        }
        del test_config['test_item_name'][test_input]
        with pytest.raises(ValueError) as excinfo:
            c_return_value = await c._validate_category_val(category_val=test_config, set_value_val_from_default_val=True)
        assert 'Missing entry_name {} for item_name {}'.format(test_input, "test_item_name") in str(excinfo.value)


    @pytest.mark.asyncio
    async def test__validate_category_val_config_without_default_notuse_value_val(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config = { 
            "test_item_name": {
                "description": "test description val",
                "type": "string",
            },
        }
        with pytest.raises(ValueError) as excinfo:
            c_return_value = await c._validate_category_val(category_val=test_config, set_value_val_from_default_val=True)
        assert 'Missing entry_name default for item_name test_item_name' in str(excinfo.value)
        

    @pytest.mark.asyncio
    async def test__validate_category_val_config_with_default_andvalue_val_notuse_value_val(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config = { 
            "test_item_name": {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                "value": "test value val"
            },
        }
        with pytest.raises(ValueError) as excinfo:
            c_return_value = await c._validate_category_val(category_val=test_config, set_value_val_from_default_val=True)
        assert 'Specifying value_name and value_val for item_name test_item_name is not allowed if desired behavior is to use default_val as value_val' in str(excinfo.value)
        
    @pytest.mark.asyncio
    async def test__merge_category_vals_same_items_different_values(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config_new = {
            "test_item_name": {
                "description": "test description val",
                "type": "string",
                "default": "test default val",
                "value": "test value val"
            },
        }
        test_config_storage = {
            "test_item_name": {
                "description": "test description val storage",
                "type": "string",
                "default": "test default val storage",
                "value": "test value val storage"
            },
        }
        c_return_value = await c._merge_category_vals(test_config_new, test_config_storage, keep_original_items=True)
        assert type(c_return_value) is dict
        assert len(c_return_value) is 1
        test_item_val = c_return_value.get("test_item_name")
        assert type(test_item_val) is dict
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
        

    @pytest.mark.asyncio
    async def test__merge_category_vals_no_mutual_items_ignore_original(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config_new = {
            "test_item_name": {
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
        c_return_value = await c._merge_category_vals(test_config_new, test_config_storage, keep_original_items=False)
        assert type(c_return_value) is dict
        # ignore "test_item_name_storage" and include "test_item_name"
        assert len(c_return_value) is 1
        test_item_val = c_return_value.get("test_item_name")
        assert type(test_item_val) is dict
        assert len(test_item_val) is 4
        assert test_item_val.get("description") is "test description val"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val"
        assert test_item_val.get("value") is "test value val"
        assert test_config_new is not c_return_value
        assert test_config_storage is not c_return_value
        assert test_config_new is not test_config_storage
        

    @pytest.mark.asyncio
    async def test__merge_category_vals_no_mutual_items_include_original(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        test_config_new = {
            "test_item_name": {
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
        c_return_value = await c._merge_category_vals(test_config_new, test_config_storage, keep_original_items=True)
        assert type(c_return_value) is dict
        # include "test_item_name_storage" and "test_item_name"
        assert len(c_return_value) is 2
        test_item_val = c_return_value.get("test_item_name")
        assert type(test_item_val) is dict
        assert len(test_item_val) is 4
        assert test_item_val.get("description") is "test description val"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val"
        assert test_item_val.get("value") is "test value val"
        test_item_val = c_return_value.get("test_item_name_storage")
        assert type(test_item_val) is dict
        assert len(test_item_val) is 4
        assert test_item_val.get("description") is "test description val storage"
        assert test_item_val.get("type") is "string"
        assert test_item_val.get("default") is "test default val storage"
        assert test_item_val.get("value") is "test value val storage"
        assert test_config_new is not c_return_value
        assert test_config_storage is not c_return_value
        assert test_config_new is not test_config_storage
        
    
    # async def _read_category_val(self, category_name)
    # TODO: check what to do 
    @pytest.mark.skip(reason="unit tests do not suffice here")
    @pytest.mark.asyncio
    async def test__read_category_val(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        return_value = await c._read_category_val(category_name)

    # async def _create_new_category(self, category_name, category_val, category_description)
    # TODO: check what to do
    @pytest.mark.skip(reason="unit tests do not suffice here")
    @pytest.mark.asyncio
    async def test__create_new_category(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        with patch.object(AuditLogger, 'information', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as auditloggerpatch:
            with patch('foglamp.common.storage_client.payload_builder.PayloadBuilder') as payloadbuilderpatch:                 
                return_value = await c._create_new_category('category_name', 'category_val', 'category_description')
        auditloggerpatch.assert_called_once_with('CONAD', {'category': 'category_val', 'name': 'category_name'})
        kall = storageClientMock.mock_calls[0]
        name, args, kwargs = kall
        assert name == 'insert_into_tbl'
        assert args[0] == 'configuration'

    # async def _read_all_category_names(self,reset_singleton)
    # TODO: check what to do
    @pytest.mark.skip(reason="unit tests do not suffice here")
    @pytest.mark.asyncio
    async def test__read_all_category_names(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        return_value = await c._read_all_category_names()

    # async def _read_item_val(self, category_name, item_name):
    # TODO: check what to do
    @pytest.mark.skip(reason="unit tests do not suffice here")
    @pytest.mark.asyncio
    async def test__read_item_val(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        return_value = await c._read_item_val(category_name, item_name)

    # async def _read_value_val(self, category_name, item_name):
    # TODO: check what to do
    @pytest.mark.skip(reason="unit tests do not suffice here")
    @pytest.mark.asyncio
    async def test__read_value_val(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        return_value = await c._read_value_val(category_name, item_name)

    # async def _update_value_val(self, category_name, item_name, new_value_val):
    # TODO: check what to do
    @pytest.mark.skip(reason="unit tests do not suffice here")
    @pytest.mark.asyncio
    async def test__update_value_val(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        return_value = await c._update_value_val(category_name, item_name, new_value_val)

    # TODO: check what to do
    # async def _update_category(self, category_name, category_val, category_description):
    @pytest.mark.skip(reason="unit tests do not suffice here")
    @pytest.mark.asyncio
    async def test__update_category(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        return_value = await c._update_category(category_name, category_val, category_description)


    
    # async def create_category(self, category_name, category_value, category_description='', keep_original_items=False):

    @pytest.mark.asyncio
    async def test_create_category_good_newval_bad_storageval_good_update(self,reset_singleton):
        async def return_not_none(return_value):
            await asyncio.sleep(.1)
            return return_value
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        with patch.object(ConfigurationManager, '_validate_category_val', side_effect=[return_not_none({}), Exception()]) as valpatch:
            with patch.object(ConfigurationManager, '_read_category_val', return_value=return_not_none({})) as readpatch:
                with patch.object(ConfigurationManager, '_merge_category_vals', return_value=return_not_none({})) as mergepatch:
                    with patch.object(ConfigurationManager, '_run_callbacks', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as callbackpatch:
                        with patch.object(ConfigurationManager, '_update_category', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as updatepatch:
                            await c.create_category('catname', 'catvalue', 'catdesc')
        valpatch.assert_has_calls([call('catvalue', True), call({}, False)])
        readpatch.assert_called_once_with('catname')
        mergepatch.assert_not_called()
        updatepatch.assert_called_once_with('catname', {}, 'catdesc')
        callbackpatch.assert_called_once_with('catname')


        
    @pytest.mark.asyncio
    async def test_create_category_good_newval_bad_storageval_bad_update(self,reset_singleton):
        async def return_not_none(return_value):
            await asyncio.sleep(.1)
            return return_value
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        with patch.object(ConfigurationManager, '_validate_category_val', side_effect=[return_not_none({}), Exception()]) as valpatch:
            with patch.object(ConfigurationManager, '_read_category_val', return_value=return_not_none({})) as readpatch:
                with patch.object(ConfigurationManager, '_merge_category_vals', return_value=return_not_none({})) as mergepatch:
                    with patch.object(ConfigurationManager, '_run_callbacks', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as callbackpatch:
                        with patch.object(ConfigurationManager, '_update_category', side_effect=Exception()) as updatepatch:
                            with pytest.raises(Exception) as excinfo:
                                await c.create_category('catname', 'catvalue', 'catdesc')
        valpatch.assert_has_calls([call('catvalue', True), call({}, False)])
        readpatch.assert_called_once_with('catname')
        mergepatch.assert_not_called()
        updatepatch.assert_called_once_with('catname', {}, 'catdesc')
        callbackpatch.assert_not_called()



    # (merged_value)
    @pytest.mark.asyncio
    async def test_create_category_good_newval_good_storageval_nochange(self,reset_singleton):
        async def return_not_none(return_value):
            await asyncio.sleep(.1)
            return return_value
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        with patch.object(ConfigurationManager, '_validate_category_val', side_effect=[return_not_none({}), return_not_none({})]) as valpatch:
            with patch.object(ConfigurationManager, '_read_category_val', return_value=return_not_none({})) as readpatch:
                with patch.object(ConfigurationManager, '_merge_category_vals', return_value=return_not_none({})) as mergepatch:
                    with patch.object(ConfigurationManager, '_run_callbacks', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as callbackpatch:
                        with patch.object(ConfigurationManager, '_update_category', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as updatepatch:
                            await c.create_category('catname', 'catvalue', 'catdesc')
        valpatch.assert_has_calls([call('catvalue', True), call({}, False)])
        readpatch.assert_called_once_with('catname')
        mergepatch.assert_called_once_with({},{},False)
        updatepatch.assert_not_called()
        callbackpatch.assert_not_called()



    @pytest.mark.asyncio
    async def test_create_category_good_newval_good_storageval_good_update(self,reset_singleton):
        async def return_not_none(return_value):
            await asyncio.sleep(.1)
            return return_value
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        with patch.object(ConfigurationManager, '_validate_category_val', side_effect=[return_not_none({}), return_not_none({})]) as valpatch:
            with patch.object(ConfigurationManager, '_read_category_val', return_value=return_not_none({})) as readpatch:
                with patch.object(ConfigurationManager, '_merge_category_vals', return_value=return_not_none({'bla':'bla'})) as mergepatch:
                    with patch.object(ConfigurationManager, '_run_callbacks', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as callbackpatch:
                        with patch.object(ConfigurationManager, '_update_category', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as updatepatch:
                            await c.create_category('catname', 'catvalue', 'catdesc')
        valpatch.assert_has_calls([call('catvalue', True), call({}, False)])
        readpatch.assert_called_once_with('catname')
        mergepatch.assert_called_once_with({},{},False)
        updatepatch.assert_called_once_with('catname', {'bla': 'bla'}, 'catdesc')
        callbackpatch.assert_called_once_with('catname')


    @pytest.mark.asyncio
    async def test_create_category_good_newval_good_storageval_bad_update(self,reset_singleton):
        async def return_not_none(return_value):
            await asyncio.sleep(.1)
            return return_value
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        with patch.object(ConfigurationManager, '_validate_category_val', side_effect=[return_not_none({}), return_not_none({})]) as valpatch:
            with patch.object(ConfigurationManager, '_read_category_val', return_value=return_not_none({})) as readpatch:
                with patch.object(ConfigurationManager, '_merge_category_vals', return_value=return_not_none({'bla':'bla'})) as mergepatch:
                    with patch.object(ConfigurationManager, '_run_callbacks', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as callbackpatch:
                        with patch.object(ConfigurationManager, '_update_category', side_effect=Exception()) as updatepatch:
                            with pytest.raises(Exception) as excinfo:
                                await c.create_category('catname', 'catvalue', 'catdesc')
        valpatch.assert_has_calls([call('catvalue', True), call({}, False)])
        readpatch.assert_called_once_with('catname')
        mergepatch.assert_called_once_with({},{},False)
        updatepatch.assert_called_once_with('catname', {'bla': 'bla'}, 'catdesc')
        callbackpatch.assert_not_called()


    @pytest.mark.asyncio
    async def test_create_category_good_newval_no_storageval_good_create(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        with patch.object(ConfigurationManager, '_validate_category_val', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as valpatch:
            with patch.object(ConfigurationManager, '_read_category_val', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as readpatch:
                with patch.object(ConfigurationManager, '_create_new_category', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as createpatch:
                    with patch.object(ConfigurationManager, '_run_callbacks', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as callbackpatch:
                        await c.create_category('catname', 'catvalue', "catdesc")
        valpatch.assert_called_once_with('catvalue', True)
        readpatch.assert_called_once_with('catname')
        createpatch.assert_called_once_with('catname', None, 'catdesc')
        callbackpatch.assert_called_once_with('catname')


    @pytest.mark.asyncio
    async def test_create_category_good_newval_no_storageval_bad_create(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        with patch.object(ConfigurationManager, '_validate_category_val', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as valpatch:
            with patch.object(ConfigurationManager, '_read_category_val', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as readpatch:
                with patch.object(ConfigurationManager, '_create_new_category', side_effect=Exception()) as createpatch:
                    with patch.object(ConfigurationManager, '_run_callbacks', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as callbackpatch:
                        with pytest.raises(Exception) as excinfo:
                            await c.create_category('catname', 'catvalue', "catdesc")
        valpatch.assert_called_once_with('catvalue', True)
        readpatch.assert_called_once_with('catname')
        createpatch.assert_called_once_with('catname', None, 'catdesc')
        callbackpatch.assert_not_called()



    @pytest.mark.asyncio
    async def test_create_category_bad_newval(self,reset_singleton):
        storageClientMock = MagicMock(spec=StorageClient)
        c = ConfigurationManager(storageClientMock)
        with patch.object(ConfigurationManager, '_validate_category_val', side_effect=Exception()) as valpatch:
            with patch.object(ConfigurationManager, '_read_category_val', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as readpatch:
                with patch.object(ConfigurationManager, '_create_new_category', side_effect=Exception()) as createpatch:
                    with patch.object(ConfigurationManager, '_run_callbacks', return_value=asyncio.ensure_future(asyncio.sleep(.1))) as callbackpatch:
                        with pytest.raises(Exception) as excinfo:
                            await c.create_category('catname', 'catvalue', "catdesc")
        valpatch.assert_called_once_with('catvalue', True)
        readpatch.assert_not_called()
        callbackpatch.assert_not_called()


"""
    async def get_all_category_names(self,reset_singleton):
    async def get_category_all_items(self, category_name):
    async def get_category_item(self, category_name, item_name):
    async def get_category_item_value_entry(self, category_name, item_name):
    async def set_category_item_value_entry(self, category_name, item_name, new_value_entry):
"""
