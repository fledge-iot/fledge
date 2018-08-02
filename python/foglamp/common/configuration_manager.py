# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

from importlib import import_module
import copy
import json
import inspect
import ipaddress

from foglamp.common.storage_client.payload_builder import PayloadBuilder
from foglamp.common.storage_client.storage_client import StorageClientAsync
from foglamp.common.storage_client.exceptions import StorageServerError
from foglamp.common.storage_client.utils import Utils
from foglamp.common import logger
from foglamp.common.audit_logger import AuditLogger

__author__ = "Ashwin Gopalakrishnan, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup(__name__)

# MAKE UPPER_CASE
_valid_type_strings = sorted(['boolean', 'integer', 'string', 'IPv4', 'IPv6', 'X509 certificate', 'password', 'JSON'])


class ConfigurationManagerSingleton(object):
    """ ConfigurationManagerSingleton

    Used to make ConfigurationManager a singleton via shared state
    """
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state


class ConfigurationManager(ConfigurationManagerSingleton):
    """ Configuration Manager

    General naming convention:

    category(s)
        category_name - string
        category_description - string
        category_val - dict
            item_name - string (dynamic)
            item_val - dict
                entry_name - string
                entry_val - string

        ----------- 4 fixed entry_name/entry_val pairs ----------------

                description_name - string (fixed - 'description')
                    description_val - string (dynamic)
                type_name - string (fixed - 'type')
                    type_val - string (dynamic - ('boolean', 'integer', 'string', 'IPv4', 'IPv6', 'X509 certificate', 'JSON'))
                default_name - string (fixed - 'default')
                    default_val - string (dynamic)
                value_name - string (fixed - 'value')
                    value_val - string (dynamic)
    """

    _storage = None
    _registered_interests = None

    def __init__(self, storage=None):
        ConfigurationManagerSingleton.__init__(self)
        if self._storage is None:
            if not isinstance(storage, StorageClientAsync):
                raise TypeError('Must be a valid Storage object')
            self._storage = storage
        if self._registered_interests is None:
            self._registered_interests = {}

    async def _run_callbacks(self, category_name):
        callbacks = self._registered_interests.get(category_name)
        if callbacks is not None:
            for callback in callbacks:
                try:
                    cb = import_module(callback)
                except ImportError:
                    _logger.exception(
                        'Unable to import callback module %s for category_name %s', callback, category_name)
                    raise
                if not hasattr(cb, 'run'):
                    _logger.exception(
                        'Callback module %s does not have method run', callback)
                    raise AttributeError('Callback module {} does not have method run'.format(callback))
                method = cb.run
                if not inspect.iscoroutinefunction(method):
                    _logger.exception(
                        'Callback module %s run method must be a coroutine function', callback)
                    raise AttributeError('Callback module {} run method must be a coroutine function'.format(callback))
                await cb.run(category_name)

    async def _merge_category_vals(self, category_val_new, category_val_storage, keep_original_items):
        # preserve all value_vals from category_val_storage
        # use items in category_val_new not in category_val_storage
        # keep_original_items = FALSE ignore items in category_val_storage not in category_val_new
        # keep_original_items = TRUE keep items in category_val_storage not in category_val_new
        category_val_storage_copy = copy.deepcopy(category_val_storage)
        category_val_new_copy = copy.deepcopy(category_val_new)
        for item_name_new, item_val_new in category_val_new_copy.items():
            item_val_storage = category_val_storage_copy.get(item_name_new)
            if item_val_storage is not None:
                item_val_new['value'] = item_val_storage.get('value')
                category_val_storage_copy.pop(item_name_new)
        if keep_original_items:
            for item_name_storage, item_val_storage in category_val_storage_copy.items():
                category_val_new_copy[item_name_storage] = item_val_storage
        return category_val_new_copy

    async def _validate_category_val(self, category_val, set_value_val_from_default_val=True):
        require_entry_value = not set_value_val_from_default_val
        if type(category_val) is not dict:
            raise TypeError('category_val must be a dictionary')
        category_val_copy = copy.deepcopy(category_val)
        for item_name, item_val in category_val_copy.items():
            if type(item_name) is not str:
                raise TypeError('item_name must be a string')
            if type(item_val) is not dict:
                raise TypeError('item_value must be a dict for item_name {}'.format(item_name))

            optional_item_entries = {'readonly': 0, 'order': 0, 'length': 0, 'maximum': 0, 'minimum': 0}
            expected_item_entries = {'description': 0, 'default': 0, 'type': 0}

            if require_entry_value:
                expected_item_entries['value'] = 0

            def get_entry_val(k):
                v = [val for name, val in item_val.items() if name == k]
                return v[0]

            for entry_name, entry_val in item_val.items():
                if type(entry_name) is not str:
                    raise TypeError('entry_name must be a string for item_name {}'.format(item_name))
                if type(entry_val) is not str:
                    raise TypeError(
                        'entry_val must be a string for item_name {} and entry_name {}'.format(item_name, entry_name))

                # If Entry item exists in optional list, then update expected item entries
                if entry_name in optional_item_entries:
                    if entry_name == 'readonly':
                        if self._validate_type_value('boolean', entry_val) is False:
                            raise ValueError('Unrecognized value for item_name {}'.format(entry_name))
                    else:
                        if self._validate_type_value('integer', entry_val) is False:
                            raise ValueError('Unrecognized value for item_name {}'.format(entry_name))

                    d = {entry_name: entry_val}
                    expected_item_entries.update(d)

                num_entries = expected_item_entries.get(entry_name)
                if set_value_val_from_default_val and entry_name == 'value':
                    raise ValueError('Specifying value_name and value_val for item_name {} is not allowed if '
                                     'desired behavior is to use default_val as value_val'.format(item_name))
                if num_entries is None:
                    raise ValueError('Unrecognized entry_name {} for item_name {}'.format(entry_name, item_name))
                if entry_name == 'type':
                    if entry_val not in _valid_type_strings:
                        raise ValueError(
                            'Invalid entry_val for entry_name "type" for item_name {}. valid: {}'.format(
                                item_name, _valid_type_strings))
                expected_item_entries[entry_name] = 1
            for needed_key, needed_value in expected_item_entries.items():
                if needed_value == 0:
                    raise ValueError('Missing entry_name {} for item_name {}'.format(needed_key, item_name))

            # validate data type value
            if self._validate_type_value(get_entry_val("type"), get_entry_val("default")) is False:
                raise ValueError('Unrecognized value for item_name {}'.format(item_name))
            if 'readonly' in item_val:
                item_val['readonly'] = self._clean('boolean', item_val['readonly'])

            if set_value_val_from_default_val:
                item_val['default'] = self._clean(item_val['type'], item_val['default'])
                item_val['value'] = item_val['default']

        return category_val_copy

    async def _create_new_category(self, category_name, category_val, category_description):
        try:
            audit = AuditLogger(self._storage)
            await audit.information('CONAD', {'name': category_name, 'category': category_val})
            payload = PayloadBuilder().INSERT(key=category_name, description=category_description,
                                              value=category_val).payload()
            result = await self._storage.insert_into_tbl("configuration", payload)
            response = result['response']
        except KeyError:
            raise ValueError(result['message'])
        except StorageServerError as ex:
            err_response = ex.error
            raise ValueError(err_response)

    async def _read_all_category_names(self):
        # SELECT configuration.key, configuration.description, configuration.value, configuration.ts FROM configuration
        payload = PayloadBuilder().SELECT("key", "description", "value", "ts") \
            .ALIAS("return", ("ts", 'timestamp')) \
            .FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")).payload()
        results = await self._storage.query_tbl_with_payload('configuration', payload)

        category_info = []
        for row in results['rows']:
            category_info.append((row['key'], row['description']))
        return category_info

    async def _read_all_groups(self, root):
        # SELECT key, description FROM configuration
        payload = PayloadBuilder().SELECT("key", "description").payload()
        all_categories = await self._storage.query_tbl_with_payload('configuration', payload)

        # SELECT DISTINCT child FROM category_children
        unique_category_children_payload = PayloadBuilder().SELECT("child").DISTINCT(["child"]).payload()
        unique_category_children = await self._storage.query_tbl_with_payload('category_children', unique_category_children_payload)

        list_child = [row['child'] for row in unique_category_children['rows']]
        list_root = []
        list_not_root = []

        for row in all_categories['rows']:
            if row["key"] in list_child:
                list_not_root.append((row["key"], row["description"]))
            else:
                list_root.append((row["key"], row["description"]))

        return list_root if root else list_not_root

    async def _read_category_val(self, category_name):
        # SELECT configuration.key, configuration.description, configuration.value,
        # configuration.ts FROM configuration WHERE configuration.key = :key_1
        payload = PayloadBuilder().SELECT("value").WHERE(["key", "=", category_name]).payload()
        results = await self._storage.query_tbl_with_payload('configuration', payload)
        for row in results['rows']:
            return row['value']

    async def _read_item_val(self, category_name, item_name):
        # SELECT configuration.value::json->'configuration' as value
        # FROM foglamp.configuration WHERE configuration.key='SENSORS'
        payload = PayloadBuilder().SELECT(("key", "description", "ts", ["value", [item_name]])) \
            .ALIAS("return", ("ts", "timestamp"), ("value", "value")) \
            .FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")) \
            .WHERE(["key", "=", category_name]).payload()

        results = await self._storage.query_tbl_with_payload('configuration', payload)
        if len(results['rows']) == 0:
            return None

        return results['rows'][0]['value']

    async def _read_value_val(self, category_name, item_name):
        # SELECT configuration.value::json->'retainUnsent'->'value' as value
        # FROM foglamp.configuration WHERE configuration.key='PURGE_READ'
        payload = PayloadBuilder().SELECT(("key", "description", "ts", ["value", [item_name, "value"]])) \
            .ALIAS("return", ("ts", "timestamp"), ("value", "value")) \
            .FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")) \
            .WHERE(["key", "=", category_name]).payload()

        results = await self._storage.query_tbl_with_payload('configuration', payload)
        if len(results['rows']) == 0:
            return None

        return results['rows'][0]['value']

    async def _update_value_val(self, category_name, item_name, new_value_val):
        try:
            old_value = await self._read_value_val(category_name, item_name)
            # UPDATE foglamp.configuration
            # SET value = jsonb_set(value, '{retainUnsent,value}', '"12"')
            # WHERE key='PURGE_READ'
            payload = PayloadBuilder().SELECT("key", "description", "ts", "value") \
                .JSON_PROPERTY(("value", [item_name, "value"], new_value_val)) \
                .FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")) \
                .WHERE(["key", "=", category_name]).payload()
            await self._storage.update_tbl("configuration", payload)
            audit = AuditLogger(self._storage)
            audit_details = {'category': category_name, 'item': item_name, 'oldValue': old_value, 'newValue': new_value_val}
            await audit.information('CONCH', audit_details)
        except KeyError as ex:
            raise ValueError(str(ex))
        except StorageServerError as ex:
            err_response = ex.error
            raise ValueError(err_response)

    async def _update_category(self, category_name, category_val, category_description):
        try:
            payload = PayloadBuilder().SET(value=category_val, description=category_description). \
                WHERE(["key", "=", category_name]).payload()
            result = await self._storage.update_tbl("configuration", payload)
            response = result['response']
        except KeyError:
            raise ValueError(result['message'])
        except StorageServerError as ex:
            err_response = ex.error
            raise ValueError(err_response)

    async def get_all_category_names(self, root=None):
        """Get all category names in the FogLAMP system

        Args:
            root: If true then select all keys from categories table and then filter out
                  that are children of another category. So the root categories are those
                  entries in configuration table that do not appear in distinct child in category_children
                  If false then it will return distinct child in category_childreb
                  If root is None then it will return all categories
        Return Values:
                    a list of tuples (string category_name, string category_description)
        """
        try:
            info = await self._read_all_groups(root) if root is not None else await self._read_all_category_names()
            return info
        except:
            _logger.exception(
                'Unable to read all category names')
            raise

    async def get_category_all_items(self, category_name):
        """Get a specified category's entire configuration (all items).

        Keyword Arguments:
        category_name -- name of the category (required)

        Return Values:
        a JSONB dictionary with all items of a category's configuration
        None
        """
        try:
            return await self._read_category_val(category_name)
        except:
            _logger.exception(
                'Unable to get all category names based on category_name %s', category_name)
            raise

    async def get_category_item(self, category_name, item_name):
        """Get a given item within a given category.

        Keyword Arguments:
        category_name -- name of the category (required)
        item_name -- name of the item within the category (required)

        Return Values:
        a JSONB dictionary with item's content
        None
        """
        try:
            return await self._read_item_val(category_name, item_name)
        except:
            _logger.exception(
                'Unable to get category item based on category_name %s and item_name %s', category_name, item_name)
            raise

    async def get_category_item_value_entry(self, category_name, item_name):
        """Get the "value" entry of a given item within a given category.

        Keyword Arguments:
        category_name -- name of the category (required)
        item_name -- name of the item within the category (required)

        Return Values:
        a string of the "value" entry
        None
        """
        try:
            return await self._read_value_val(category_name, item_name)
        except:
            _logger.exception(
                'Unable to get the "value" entry based on category_name %s and item_name %s', category_name,
                item_name)
            raise

    async def set_category_item_value_entry(self, category_name, item_name, new_value_entry):
        """Set the "value" entry of a given item within a given category.

        Keyword Arguments:
        category_name -- name of the category (required)
        item_name -- name of item within the category whose "value" entry needs to be changed (required)
        new_value_entry -- new value entry to replace old value entry

        Side Effects:
        An update to storage will not be issued if a new_value_entry is the same as the new_value_entry from storage.
        Registered callbacks will be invoked only if an update is issued.

        Exceptions Raised:
        ImportError if callback module does not exist for relevant callbacks
        AttributeError if callback module does not implement run(category_name) for relevant callbacks

        Return Values:
        None
        """
        try:
            # get storage_value_entry and compare against new_value_value with its type, update if different
            storage_value_entry = await self._read_item_val(category_name, item_name)
            # check for category_name and item_name combination existence in storage
            if storage_value_entry is None:
                raise ValueError("No detail found for the category_name: {} and item_name: {}"
                                 .format(category_name, item_name))
            if storage_value_entry == new_value_entry:
                return

            if self._validate_type_value(storage_value_entry['type'], new_value_entry) is False:
                raise TypeError('Unrecognized value name for item_name {}'.format(item_name))

            new_value_entry = self._clean(storage_value_entry['type'], new_value_entry)
            await self._update_value_val(category_name, item_name, new_value_entry)
        except:
            _logger.exception(
                'Unable to set item value entry based on category_name %s and item_name %s and value_item_entry %s',
                category_name, item_name, new_value_entry)
            raise
        try:
            await self._run_callbacks(category_name)
        except:
            _logger.exception(
                'Unable to run callbacks for category_name %s', category_name)
            raise

    async def create_category(self, category_name, category_value, category_description='', keep_original_items=False):
        """Create a new category in the database.

        Keyword Arguments:
        category_name -- name of the category (required)
        category_json_schema -- JSONB object in dictionary form representing category's configuration values
                sample_category_json_schema = {
                    "item_name1": {
                        "description": "Port to listen on",
                        "default": "5432",
                        "type": "integer"
                    }
                    "port": {
                        "description": "Port to listen on",
                        "default": "5432",
                        "type": "integer"
                    },
                    "url": {
                        "description": "URL to accept data on",
                        "default": "sensor/reading-values",
                        "type": "string"
                    },
                    "certificate": {
                        "description": "X509 certificate used to identify ingress interface",
                        "default": "",
                        "type": "x509 certificate"
                    }
                }

        category_description -- description of the category (default='')
        keep_original_items -- keep items in storage's category_val that are not in the new category_val (removes side effect #3) (default=False)

        Return Values:
        None

        Side Effects:
        A "value" entry will be created for each item using the "Default" entry's specified value.
        If a category of this name already exists within the storage, the new category_val and the storage's category_val will be merged such that:
            1. preserve all "value" entries from the storage's category val
            2. use items in the new category_val that are not in the storage's category_val
            3. ignore items in storage's category_val that are not in the new category_val
        An update to storage will not be issued if a merged category_value is the same as the category_value from storage.
        Registered callbacks specific to the category_name will be invoked only if a new category is created or if a category is updated.

        Exceptions Raised:
        ValueError
        TypeError
        ImportError if callback module does not exist for relevant callbacks
        AttributeError if callback module does not implement run(category_name) for relevant callbacks

        Restrictions and Usage:
        A FogLAMP component calls this method to create one or more new configuration categories to store initial configuration.
        Only default values can be entered for and item's entries.
        A "value" entry specified for an item will raise an exception.
        """
        if not isinstance(category_name, str):
            raise TypeError('category_name must be a string')

        if not isinstance(category_description, str):
            raise TypeError('category_description must be a string')

        category_val_prepared = ''
        try:
            # validate new category_val, set "value" from default
            category_val_prepared = await self._validate_category_val(category_value, True)
            # check if category_name is already in storage
            category_val_storage = await self._read_category_val(category_name)
            if category_val_storage is None:
                await self._create_new_category(category_name, category_val_prepared, category_description)
            else:
                # validate category_val from storage, do not set "value" from default, reuse from storage value
                try:
                    category_val_storage = await self._validate_category_val(category_val_storage, False)
                # if validating category from storage fails, nothing to salvage from storage, use new completely
                except:
                    _logger.exception(
                        'category_value for category_name %s from storage is corrupted; using category_value without merge',
                        category_name)
                # if validating category from storage succeeds, merge new and storage
                else:
                    category_val_prepared = await self._merge_category_vals(category_val_prepared, category_val_storage,
                                                                            keep_original_items)
                    if json.dumps(category_val_prepared, sort_keys=True) == json.dumps(category_val_storage,
                                                                                       sort_keys=True):
                        return
                await self._update_category(category_name, category_val_prepared, category_description)
        except:
            _logger.exception(
                'Unable to create new category based on category_name %s and category_description %s and category_json_schema %s',
                category_name, category_description, category_val_prepared)
            raise
        try:
            await self._run_callbacks(category_name)
        except:
            _logger.exception(
                'Unable to run callbacks for category_name %s', category_name)
            raise
        return None

    async def _read_all_child_category_names(self, category_name):
        _children = []
        payload = PayloadBuilder().SELECT("parent", "child").WHERE(["parent", "=", category_name]).payload()
        results = await self._storage.query_tbl_with_payload('category_children', payload)
        for row in results['rows']:
            _children.append(row)

        return _children

    async def _read_child_info(self, child_list):
        info = []
        for item in child_list:
            payload = PayloadBuilder().SELECT("key", "description").WHERE(["key", "=", item['child']]).payload()
            results = await self._storage.query_tbl_with_payload('configuration', payload)
            for row in results['rows']:
                info.append(row)

        return info

    async def _create_child(self, category_name, child):
        # FIXME: Handle the case if re-create same data, it throws UNIQUE constraint failed
        try:
            payload = PayloadBuilder().INSERT(parent=category_name, child=child).payload()
            result = await self._storage.insert_into_tbl("category_children", payload)
            response = result['response']
        except KeyError:
            raise ValueError(result['message'])
        except StorageServerError as ex:
            err_response = ex.error
            raise ValueError(err_response)

        return response

    async def get_category_child(self, category_name):
        """Get the list of categories that are children of a given category.

        Keyword Arguments:
        category_name -- name of the category (required)

        Return Values:
        JSON
        """
        category = await self._read_category_val(category_name)
        if category is None:
            raise ValueError('No such {} category exist'.format(category_name))

        try:
            child_cat_names = await self._read_all_child_category_names(category_name)
            return await self._read_child_info(child_cat_names)
        except:
            _logger.exception(
                'Unable to read all child category names')
            raise

    async def create_child_category(self, category_name, children):
        """Create a new child category in the database.

        Keyword Arguments:
        category_name -- name of the category (required)
        children -- an array of child categories

        Return Values:
        JSON
        """
        def diff(lst1, lst2):
            return [v for v in lst2 if v not in lst1]

        if not isinstance(category_name, str):
            raise TypeError('category_name must be a string')

        if not isinstance(children, list):
            raise TypeError('children must be a list')

        try:
            category = await self._read_category_val(category_name)
            if category is None:
                raise ValueError('No such {} category exist'.format(category_name))

            for child in children:
                category = await self._read_category_val(child)
                if category is None:
                    raise ValueError('No such {} child exist'.format(child))

            # Read children from storage
            _existing_children = await self._read_all_child_category_names(category_name)
            children_from_storage = [item['child'] for item in _existing_children]
            # Diff in existing children and requested children
            new_children = diff(children_from_storage, children)
            for a_new_child in new_children:
                result = await self._create_child(category_name, a_new_child)
                children_from_storage.append(a_new_child)

            return {"children": children_from_storage}

            # TODO: [TO BE DECIDED] - Audit Trail Entry
        except KeyError:
            raise ValueError(result['message'])

    async def delete_child_category(self, category_name, child_category):
        """Delete a parent-child relationship

        Keyword Arguments:
        category_name -- name of the category (required)
        child_category -- child name

        Return Values:
        JSON
        """
        if not isinstance(category_name, str):
            raise TypeError('category_name must be a string')

        if not isinstance(child_category, str):
            raise TypeError('child_category must be a string')

        category = await self._read_category_val(category_name)
        if category is None:
            raise ValueError('No such {} category exist'.format(category_name))

        child = await self._read_category_val(child_category)
        if child is None:
            raise ValueError('No such {} child exist'.format(child_category))

        try:
            payload = PayloadBuilder().WHERE(["parent", "=", category_name]).AND_WHERE(["child", "=", child_category]).payload()
            result = await self._storage.delete_from_tbl("category_children", payload)

            if result['response'] == 'deleted':
                child_dict = await self._read_all_child_category_names(category_name)
                _children = []
                for item in child_dict:
                    _children.append(item['child'])

            # TODO: Shall we write audit trail code entry here? log_code?

        except KeyError:
            raise ValueError(result['message'])
        except StorageServerError as ex:
            err_response = ex.error
            raise ValueError(err_response)

        return _children

    async def delete_parent_category(self, category_name):
        """Delete a parent-child relationship for a parent

        Keyword Arguments:
        category_name -- name of the category (required)

        Return Values:
        JSON
        """
        if not isinstance(category_name, str):
            raise TypeError('category_name must be a string')

        category = await self._read_category_val(category_name)
        if category is None:
            raise ValueError('No such {} category exist'.format(category_name))

        try:
            payload = PayloadBuilder().WHERE(["parent", "=", category_name]).payload()
            result = await self._storage.delete_from_tbl("category_children", payload)
            response = result["response"]
            # TODO: Shall we write audit trail code entry here? log_code?

        except KeyError:
            raise ValueError(result['message'])
        except StorageServerError as ex:
            err_response = ex.error
            raise ValueError(err_response)

        return result

    def register_interest(self, category_name, callback):
        """Registers an interest in any changes to the category_value associated with category_name

        Keyword Arguments:
        category_name -- name of the category_name of interest (required)
        callback -- module with implementation of async method run(category_name) to be called when change is made to category_value

        Return Values:
        None

        Side Effects:
        Registers an interest in any changes to the category_value of a given category_name.
        This interest is maintained in memory only, and not persisted in storage.

        Restrictions and Usage:
        A particular category_name may have multiple registered interests, aka multiple callbacks associated with a single category_name.
        One or more category_names may use the same callback when a change is made to the corresponding category_value.
        User must implement the callback code.
        For example, if a callback is 'foglamp.callback', then user must implement foglamp/callback.py module with method run(category_name).
        A callback is only called if the corresponding category_value is created or updated.
        A callback is not called if the corresponding category_description is updated.
        A change in configuration is not rolled back if callbacks fail.
        """
        if category_name is None:
            raise ValueError('Failed to register interest. category_name cannot be None')
        if callback is None:
            raise ValueError('Failed to register interest. callback cannot be None')
        if self._registered_interests.get(category_name) is None:
            self._registered_interests[category_name] = {callback}
        else:
            self._registered_interests[category_name].add(callback)

    def unregister_interest(self, category_name, callback):
        """Unregisters an interest in any changes to the category_value associated with category_name

        Keyword Arguments:
        category_name -- name of the category_name of interest (required)
        callback -- module with implementation of async method run(category_name) to be called when change is made to category_value

        Return Values:
        None

        Side Effects:
        Unregisters an interest in any changes to the category_value of a given category_name with the associated callback.
        This interest is maintained in memory only, and not persisted in storage.

        Restrictions and Usage:
        A particular category_name may have multiple registered interests, aka multiple callbacks associated with a single category_name.
        One or more category_names may use the same callback when a change is made to the corresponding category_value.
        """
        if category_name is None:
            raise ValueError('Failed to unregister interest. category_name cannot be None')
        if callback is None:
            raise ValueError('Failed to unregister interest. callback cannot be None')
        if self._registered_interests.get(category_name) is not None:
            if callback in self._registered_interests[category_name]:
                self._registered_interests[category_name].discard(callback)
                if len(self._registered_interests[category_name]) == 0:
                    del self._registered_interests[category_name]

    def _validate_type_value(self, _type, _value):
        # TODO: Not implemented for password and X509 certificate type
        def _str_to_bool(item_val):
            return item_val.lower() in ("true", "false")

        def _str_to_int(item_val):
            try:
                _value = int(item_val)
            except ValueError:
                return False
            else:
                return True

        def _str_to_ipaddress(item_val):
            try:
                return ipaddress.ip_address(item_val)
            except ValueError:
                return False

        if _type == 'boolean':
            return _str_to_bool(_value)
        elif _type == 'integer':
            return _str_to_int(_value)
        elif _type == 'JSON':
            if isinstance(_value, dict):
                return True
            return Utils.is_json(_value)
        elif _type == 'IPv4' or _type == 'IPv6':
            return _str_to_ipaddress(_value)

    def _clean(self, item_type, item_val):
        if item_type == 'boolean':
            return item_val.lower()

        return item_val
