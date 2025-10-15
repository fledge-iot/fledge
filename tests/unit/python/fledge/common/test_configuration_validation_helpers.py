# -*- coding: utf-8 -*-

"""
Unit tests for validation helper methods in ConfigurationManager.

This test file specifically tests the helper methods extracted from _validate_list_type
and other validation helper methods:
- _validate_optional_string_attribute
- _validate_permissions_entry
- _validate_enumeration_type
- _validate_bucket_type
- _validate_list_items_object
- _validate_list_items_enumeration
- _validate_list_default_values
- _validate_enumeration_default_values
- _validate_items_entry
"""

import pytest
from unittest.mock import MagicMock
from fledge.common.configuration_manager import ConfigurationManager, ConfigurationManagerSingleton
from fledge.common.storage_client.storage_client import StorageClientAsync

__author__ = "Devki Nandan Ghildiyal"
__copyright__ = "Copyright (c) 2025 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

CAT_NAME = 'test_category'
ITEM_NAME = "test_item"


class TestConfigurationManagerRefactoredHelpers:
    """Test suite for refactored helper methods extracted from _validate_list_type."""

    @pytest.fixture()
    def reset_singleton(self):
        """Reset singleton state before and after each test."""
        ConfigurationManagerSingleton._shared_state = {}
        yield
        ConfigurationManagerSingleton._shared_state = {}

    @pytest.fixture()
    def config_mgr(self, reset_singleton):
        """Create a ConfigurationManager instance for testing."""
        storage_client_mock = MagicMock(spec=StorageClientAsync)
        return ConfigurationManager(storage_client_mock)

    # ==================== Tests for _validate_optional_string_attribute ====================

    @pytest.mark.parametrize("attr_name,input_value,expected", [
        ("displayName", "Valid Display Name", "Valid Display Name"),
        ("listName", "ValidListName", "ValidListName"),
        ("keyName", "  Display Name  ", "Display Name"),  # whitespace trim
        ("keyDescription", "  Test  ", "Test"),
        ("rule", "value > 0", "value > 0"),
        ("validity", "^[a-z]+$", "^[a-z]+$"),
    ])
    def test_validate_optional_string_attribute_valid(self, config_mgr, attr_name, input_value, expected):
        """Test _validate_optional_string_attribute with valid inputs."""
        result = config_mgr._validate_optional_string_attribute(
            CAT_NAME, attr_name, input_value, ITEM_NAME
        )
        assert result == expected

    @pytest.mark.parametrize("attr_name,invalid_value,error_type,error_msg", [
        ("displayName", 123, TypeError, "displayName type must be a string"),
        ("listName", True, TypeError, "listName type must be a string"),
        ("keyName", [], TypeError, "keyName type must be a string"),
        ("displayName", "", ValueError, "displayName cannot be empty"),
        ("listName", "   ", ValueError, "listName cannot be empty"),
        ("keyDescription", "\t\n", ValueError, "keyDescription cannot be empty"),
    ])
    def test_validate_optional_string_attribute_invalid(self, config_mgr, attr_name, invalid_value, error_type, error_msg):
        """Test _validate_optional_string_attribute with invalid inputs."""
        with pytest.raises(error_type) as excinfo:
            config_mgr._validate_optional_string_attribute(
                CAT_NAME, attr_name, invalid_value, ITEM_NAME
            )
        assert error_msg in str(excinfo.value)

    # ==================== Tests for _validate_permissions_entry ====================

    @pytest.mark.parametrize("permissions", [
        ["admin"],
        ["admin", "user"],
        ["admin", "user", "editor", "viewer"],
    ])
    def test_validate_permissions_entry_valid(self, config_mgr, permissions):
        """Test _validate_permissions_entry with valid permission lists."""
        # Should not raise any exception
        config_mgr._validate_permissions_entry(CAT_NAME, 'permissions', ITEM_NAME, permissions)

    @pytest.mark.parametrize("invalid_permissions,error_msg", [
        ("admin", "permissions entry value must be a list"),
        (123, "permissions entry value must be a list"),
        ([], "permissions entry value must not be empty"),
        (["admin", 123], "permissions entry values must be a string and non-empty"),
        (["admin", ""], "permissions entry values must be a string and non-empty"),
        (["admin", None], "permissions entry values must be a string and non-empty"),
        (["", "user"], "permissions entry values must be a string and non-empty"),
    ])
    def test_validate_permissions_entry_invalid(self, config_mgr, invalid_permissions, error_msg):
        """Test _validate_permissions_entry with invalid inputs."""
        with pytest.raises(ValueError) as excinfo:
            config_mgr._validate_permissions_entry(CAT_NAME, 'permissions', ITEM_NAME, invalid_permissions)
        assert error_msg in str(excinfo.value)

    # ==================== Tests for _validate_enumeration_type ====================

    def test_validate_enumeration_type_valid_options(self, config_mgr):
        """Test _validate_enumeration_type with valid options."""
        item_val = {
            "type": "enumeration",
            "options": ["option1", "option2", "option3"],
            "default": "option1"
        }
        def get_entry_val(key):
            return item_val.get(key)
        
        updates = config_mgr._validate_enumeration_type(
            CAT_NAME, ITEM_NAME, item_val, "options", item_val["options"], get_entry_val
        )
        assert "options" in updates
        assert updates["options"] == ["option1", "option2", "option3"]

    def test_validate_enumeration_type_with_permissions(self, config_mgr):
        """Test _validate_enumeration_type with permissions."""
        item_val = {
            "type": "enumeration",
            "options": ["opt1", "opt2"],
            "default": "opt1",
            "permissions": ["admin"]
        }
        def get_entry_val(key):
            return item_val.get(key)
        
        # Should not raise any exception
        config_mgr._validate_enumeration_type(
            CAT_NAME, ITEM_NAME, item_val, "permissions", ["admin"], get_entry_val
        )

    @pytest.mark.parametrize("item_val,entry_name,entry_val,error_type,error_msg", [
        # Missing options
        ({"type": "enumeration", "default": "opt1"}, "default", "opt1", KeyError, "options required for enumeration type"),
        # Options not list
        ({"type": "enumeration", "options": "not_list", "default": "opt1"}, "options", "not_list", TypeError, "entry value must be a list"),
        # Empty options
        ({"type": "enumeration", "options": [], "default": "opt1"}, "options", [], ValueError, "entry value cannot be empty list"),
        # Default not in options
        ({"type": "enumeration", "options": ["opt1", "opt2"], "default": "invalid"}, "options", ["opt1", "opt2"], ValueError, "entry value does not exist in options list"),
        # Non-string entry value
        ({"type": "enumeration", "options": ["opt1"], "default": "opt1"}, "default", 123, TypeError, "entry value must be a string"),
    ])
    def test_validate_enumeration_type_invalid(self, config_mgr, item_val, entry_name, entry_val, error_type, error_msg):
        """Test _validate_enumeration_type with invalid inputs."""
        def get_entry_val(key):
            return item_val.get(key)
        
        with pytest.raises(error_type) as excinfo:
            config_mgr._validate_enumeration_type(
                CAT_NAME, ITEM_NAME, item_val, entry_name, entry_val, get_entry_val
            )
        assert error_msg in str(excinfo.value)

    # ==================== Tests for _validate_bucket_type ====================

    def test_validate_bucket_type_valid_properties(self, config_mgr):
        """Test _validate_bucket_type with valid properties."""
        item_val = {
            "type": "bucket",
            "properties": {"key": "bucketName", "description": "Test bucket"},
            "default": ""
        }
        def get_entry_val(key):
            return item_val.get(key)
        
        updates = config_mgr._validate_bucket_type(
            CAT_NAME, ITEM_NAME, item_val, "properties", item_val["properties"], get_entry_val
        )
        assert "properties" in updates

    def test_validate_bucket_type_with_permissions(self, config_mgr):
        """Test _validate_bucket_type with valid permissions."""
        item_val = {
            "type": "bucket",
            "properties": {"key": "bucketName"},
            "permissions": ["admin", "user"],
            "default": ""
        }
        def get_entry_val(key):
            return item_val.get(key)
        
        # Should not raise any exception
        config_mgr._validate_bucket_type(
            CAT_NAME, ITEM_NAME, item_val, "properties", item_val["properties"], get_entry_val
        )

    @pytest.mark.parametrize("item_val,entry_name,entry_val,error_type,error_msg", [
        # Missing properties
        ({"type": "bucket", "default": ""}, "default", "", KeyError, "properties KV pair must be required"),
        # Properties not dict
        ({"type": "bucket", "properties": "not_dict", "default": ""}, "properties", "not_dict", ValueError, "properties must be JSON object"),
        # Empty properties
        ({"type": "bucket", "properties": {}, "default": ""}, "properties", {}, ValueError, "properties JSON object cannot be empty"),
        # Missing key in properties
        ({"type": "bucket", "properties": {"desc": "test"}, "default": ""}, "properties", {"desc": "test"}, ValueError, "key KV pair must exist in properties"),
        # Non-string entry value
        ({"type": "bucket", "properties": {"key": "test"}, "default": ""}, "default", 123, TypeError, "entry value must be a string"),
        # Invalid permissions
        ({"type": "bucket", "properties": {"key": "test"}, "permissions": "not_list", "default": ""}, "default", "", ValueError, "permissions entry value must be a list"),
    ])
    def test_validate_bucket_type_invalid(self, config_mgr, item_val, entry_name, entry_val, error_type, error_msg):
        """Test _validate_bucket_type with invalid inputs."""
        def get_entry_val(key):
            return item_val.get(key)
        
        with pytest.raises(error_type) as excinfo:
            config_mgr._validate_bucket_type(
                CAT_NAME, ITEM_NAME, item_val, entry_name, entry_val, get_entry_val
            )
        assert error_msg in str(excinfo.value)

    # ==================== Tests for _validate_list_items_object ====================

    def test_validate_list_items_object_valid(self, config_mgr):
        """Test _validate_list_items_object with valid properties structure."""
        prop_val = {
            "width": {"description": "Width", "type": "integer", "default": "100"},
            "height": {"description": "Height", "type": "integer", "default": "200"}
        }
        # Should not raise any exception
        config_mgr._validate_list_items_object(CAT_NAME, ITEM_NAME, prop_val)

    @pytest.mark.parametrize("prop_val,error_type,error_msg", [
        # Not dict
        ("not_a_dict", ValueError, "properties must be JSON object"),
        # Empty dict
        ({}, ValueError, "properties JSON object cannot be empty"),
        # Property not dict
        ({"width": "string"}, TypeError, "Properties must be a JSON object"),
        # Empty property
        ({"width": {}}, ValueError, "properties cannot be empty"),
        # Missing type key
        ({"width": {"description": "W", "default": "100"}}, ValueError, "must have type, description, default keys"),
        # Missing description key
        ({"width": {"type": "integer", "default": "100"}}, ValueError, "must have type, description, default keys"),
        # Missing default key
        ({"width": {"type": "integer", "description": "W"}}, ValueError, "must have type, description, default keys"),
    ])
    def test_validate_list_items_object_invalid(self, config_mgr, prop_val, error_type, error_msg):
        """Test _validate_list_items_object with invalid inputs."""
        with pytest.raises(error_type) as excinfo:
            config_mgr._validate_list_items_object(CAT_NAME, ITEM_NAME, prop_val)
        assert error_msg in str(excinfo.value)

    # ==================== Tests for _validate_list_items_enumeration ====================

    def test_validate_list_items_enumeration_valid(self, config_mgr):
        """Test _validate_list_items_enumeration with valid options."""
        item_val = {"type": "list", "items": "enumeration", "options": ["opt1", "opt2", "opt3"]}
        # Should not raise any exception
        config_mgr._validate_list_items_enumeration(CAT_NAME, ITEM_NAME, item_val, "items")

    @pytest.mark.parametrize("item_val,error_type,error_msg", [
        # Missing options
        ({"type": "list", "items": "enumeration"}, KeyError, "options required"),
        # Options not list
        ({"type": "list", "items": "enumeration", "options": "not_list"}, TypeError, "entry value must be a list"),
        # Empty options
        ({"type": "list", "items": "enumeration", "options": []}, ValueError, "options cannot be empty list"),
    ])
    def test_validate_list_items_enumeration_invalid(self, config_mgr, item_val, error_type, error_msg):
        """Test _validate_list_items_enumeration with invalid inputs."""
        with pytest.raises(error_type) as excinfo:
            config_mgr._validate_list_items_enumeration(CAT_NAME, ITEM_NAME, item_val, "items")
        assert error_msg in str(excinfo.value)

    # ==================== Tests for _validate_list_default_values ====================

    @pytest.mark.parametrize("item_type,entry_val,default_val,list_size", [
        # List of strings
        ("list", "string", '["value1", "value2", "value3"]', -1),
        # List of integers
        ("list", "integer", '["1", "2", "3"]', -1),
        # List of floats
        ("list", "float", '["1.5", "2.7", "3.14"]', -1),
        # KVList of strings
        ("kvlist", "string", '{"key1": "value1", "key2": "value2"}', -1),
        # List with size limit
        ("list", "string", '["a", "b"]', 3),
        # KVList with size limit
        ("kvlist", "integer", '{"k1": "1", "k2": "2"}', 5),
    ])
    def test_validate_list_default_values_valid(self, config_mgr, item_type, entry_val, default_val, list_size):
        """Test _validate_list_default_values with valid inputs."""
        item_val = {"type": item_type}
        # Should not raise any exception
        config_mgr._validate_list_default_values(CAT_NAME, ITEM_NAME, item_val, entry_val, default_val, list_size)

    @pytest.mark.parametrize("item_type,entry_val,default_val,list_size,error_type,error_msg", [
        # List with duplicates
        ("list", "string", '["val1", "val2", "val1"]', -1, ValueError, "elements are not unique"),
        # KVList with duplicate keys
        ("kvlist", "string", '{"key1": "v1", "key1": "v2"}', -1, ValueError, "duplicate KV pair found"),
        # Exceeds list size
        ("list", "string", '["1", "2", "3", "4", "5"]', 3, ValueError, "list size limit to 3"),
        # Invalid format
        ("list", "string", "not_a_valid_list", -1, TypeError, "should be passed array list in string format"),
        # Type mismatch integer
        ("list", "integer", '["1", "2", "not_int"]', -1, ValueError, "all elements should be of same"),
        # Type mismatch float
        ("list", "float", '["1.5", "not_float"]', -1, ValueError, "all elements should be of same"),
        # KVList not dict
        ("kvlist", "string", '["not", "dict"]', -1, TypeError, "KV pair invalid in default value"),
    ])
    def test_validate_list_default_values_invalid(self, config_mgr, item_type, entry_val, default_val, list_size, error_type, error_msg):
        """Test _validate_list_default_values with invalid inputs."""
        item_val = {"type": item_type}
        with pytest.raises(error_type) as excinfo:
            config_mgr._validate_list_default_values(CAT_NAME, ITEM_NAME, item_val, entry_val, default_val, list_size)
        assert error_msg in str(excinfo.value)

    # ==================== Tests for _validate_enumeration_default_values ====================

    @pytest.mark.parametrize("item_type,options,default_val", [
        # List enumeration
        ("list", ["option1", "option2", "option3"], '["option1", "option3"]'),
        # KVList enumeration
        ("kvlist", ["opt1", "opt2", "opt3"], '{"key1": "opt1", "key2": "opt2"}'),
        # Single option
        ("list", ["only_option"], '["only_option"]'),
        # All options
        ("kvlist", ["a", "b"], '{"k1": "a", "k2": "b"}'),
    ])
    def test_validate_enumeration_default_values_valid(self, config_mgr, item_type, options, default_val):
        """Test _validate_enumeration_default_values with valid inputs."""
        item_val = {"type": item_type, "items": "enumeration", "options": options}
        # Should not raise any exception
        config_mgr._validate_enumeration_default_values(CAT_NAME, ITEM_NAME, item_val, default_val)

    @pytest.mark.parametrize("item_type,options,default_val,error_msg", [
        # List with invalid option
        ("list", ["option1", "option2"], '["option1", "invalid"]', "value does not exist in options"),
        # KVList with invalid option
        ("kvlist", ["opt1", "opt2"], '{"key1": "opt1", "key2": "invalid"}', "value does not exist in options"),
    ])
    def test_validate_enumeration_default_values_invalid(self, config_mgr, item_type, options, default_val, error_msg):
        """Test _validate_enumeration_default_values with invalid inputs."""
        item_val = {"type": item_type, "items": "enumeration", "options": options}
        with pytest.raises(ValueError) as excinfo:
            config_mgr._validate_enumeration_default_values(CAT_NAME, ITEM_NAME, item_val, default_val)
        assert error_msg in str(excinfo.value)

    # ==================== Tests for _validate_items_entry ====================

    @pytest.mark.parametrize("items_type,default_val,extra_config", [
        # String type
        ("string", '["test1", "test2"]', {}),
        # Integer type
        ("integer", '["1", "2", "3"]', {}),
        # Float type
        ("float", '["1.5", "2.7"]', {}),
        # Object type
        ("object", "[]", {"properties": {"width": {"description": "W", "type": "integer", "default": "100"}}}),
        # Enumeration type
        ("enumeration", '["opt1"]', {"options": ["opt1", "opt2"]}),
        # With listSize
        ("string", '["a", "b"]', {"listSize": "2"}),
    ])
    def test_validate_items_entry_valid(self, config_mgr, items_type, default_val, extra_config):
        """Test _validate_items_entry with valid inputs."""
        item_val = {"type": "list", "items": items_type, **extra_config}
        def get_entry_val(key):
            if key == "default":
                return default_val
            if key == "properties" and "properties" in item_val:
                return item_val["properties"]
            return None
        
        # Should not raise any exception
        config_mgr._validate_items_entry(CAT_NAME, ITEM_NAME, item_val, "items", items_type, get_entry_val)

    @pytest.mark.parametrize("item_val,entry_val,error_type,error_msg", [
        # Invalid type
        ({"type": "list", "items": "invalid"}, "invalid", ValueError, "items value should either be in string, float, integer, object or enumeration"),
        # Object missing properties
        ({"type": "list", "items": "object"}, "object", KeyError, "properties KV pair must be required"),
        # listSize invalid type
        ({"type": "list", "items": "string", "listSize": 2}, "string", TypeError, "listSize type must be a string"),
        # listSize not integer
        ({"type": "list", "items": "string", "listSize": "not_num"}, "string", ValueError, "listSize value must be an integer value"),
    ])
    def test_validate_items_entry_invalid(self, config_mgr, item_val, entry_val, error_type, error_msg):
        """Test _validate_items_entry with invalid inputs."""
        def get_entry_val(key):
            return "[]"
        
        with pytest.raises(error_type) as excinfo:
            config_mgr._validate_items_entry(CAT_NAME, ITEM_NAME, item_val, "items", entry_val, get_entry_val)
        assert error_msg in str(excinfo.value)

    # ==================== Integration Tests ====================

    @pytest.mark.parametrize("item_config,entry_val,default_val", [
        # Complete list workflow
        ({"type": "list", "items": "integer", "listSize": "5"}, "integer", '["1", "2", "3"]'),
        # Complete kvlist workflow
        ({"type": "kvlist", "items": "string", "listSize": "3"}, "string", '{"key1": "val1", "key2": "val2"}'),
        # Object with complex properties
        (
            {
                "type": "list",
                "items": "object",
                "properties": {
                    "name": {"description": "Name", "type": "string", "default": ""},
                    "age": {"description": "Age", "type": "integer", "default": "0"},
                    "score": {"description": "Score", "type": "float", "default": "0.0"}
                }
            },
            "object",
            "[]"
        ),
    ])
    def test_validate_items_entry_integration(self, config_mgr, item_config, entry_val, default_val):
        """Integration tests for complete validation workflows."""
        item_val = item_config.copy()
        def get_entry_val(key):
            if key == "default":
                return default_val
            if key == "properties" and "properties" in item_val:
                return item_val["properties"]
            return None
        
        # Should validate successfully
        config_mgr._validate_items_entry(CAT_NAME, ITEM_NAME, item_val, "items", entry_val, get_entry_val)

    def test_validate_enumeration_default_values_integration(self, config_mgr):
        """Integration test for enumeration with all options."""
        item_val = {
            "type": "list",
            "items": "enumeration",
            "options": ["red", "green", "blue", "yellow"]
        }
        default_val = '["red", "blue", "yellow"]'
        
        # Should validate successfully
        config_mgr._validate_enumeration_default_values(CAT_NAME, ITEM_NAME, item_val, default_val)
