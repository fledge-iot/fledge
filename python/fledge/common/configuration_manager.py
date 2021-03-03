# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from importlib import import_module
from urllib.parse import urlparse
import binascii
import copy
import json
import inspect
import ipaddress
import datetime
import os
from math import *
import collections
import ast

from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.storage_client import StorageClientAsync
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.storage_client.utils import Utils
from fledge.common import logger
from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_DATA
from fledge.common.audit_logger import AuditLogger

__author__ = "Ashwin Gopalakrishnan, Ashish Jabble, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup(__name__)

# MAKE UPPER_CASE
_valid_type_strings = sorted(['boolean', 'integer', 'float', 'string', 'IPv4', 'IPv6', 'X509 certificate', 'password',
                              'JSON', 'URL', 'enumeration', 'script', 'code', 'northTask'])
_optional_items = sorted(['readonly', 'order', 'length', 'maximum', 'minimum', 'rule', 'deprecated', 'displayName',
                          'validity', 'mandatory'])
RESERVED_CATG = ['South', 'North', 'General', 'Advanced', 'Utilities', 'rest_api', 'Security', 'service', 'SCHEDULER',
                 'SMNTR', 'PURGE_READ', 'Notifications']


class ConfigurationCache(object):
    """Configuration Cache Manager"""

    MAX_CACHE_SIZE = 10

    def __init__(self):
        """
        cache: value stored in dictionary as per category_name
        max_cache_size: Hold the 10 recently requested categories in the cache
        hit: number of times an item is read from the cache
        miss: number of times an item was not found in the cache and a read of the storage layer was required
        """
        self.cache = {}
        self.max_cache_size = self.MAX_CACHE_SIZE
        self.hit = 0
        self.miss = 0

    def __contains__(self, category_name):
        """Returns True or False depending on whether or not the key is in the cache
        and update the hit and data_accessed"""
        if category_name in self.cache:
            try:
                current_hit = self.cache[category_name]['hit']
            except KeyError:
                current_hit = 0

            self.hit += 1
            self.cache[category_name].update({'date_accessed': datetime.datetime.now(), 'hit': current_hit + 1})
            return True
        self.miss += 1
        return False

    def update(self, category_name, category_description, category_val, display_name=None):
        """Update the cache dictionary and remove the oldest item"""
        if category_name not in self.cache and len(self.cache) >= self.max_cache_size:
            self.remove_oldest()
        display_name = category_name if display_name is None else display_name
        self.cache[category_name] = {'date_accessed': datetime.datetime.now(), 'description': category_description,
                                     'value': category_val, 'displayName': display_name}
        _logger.info("Updated Configuration Cache %s", self.cache)

    def remove_oldest(self):
        """Remove the entry that has the oldest accessed date"""
        oldest_entry = None
        for category_name in self.cache:
            if oldest_entry is None:
                oldest_entry = category_name
            elif self.cache[category_name]['date_accessed'] < self.cache[oldest_entry]['date_accessed']:
                oldest_entry = category_name
        self.cache.pop(oldest_entry)

    def remove(self, key):
        """Remove the entry with given key name"""
        for category_name in self.cache:
            if key == category_name:
                self.cache.pop(key)
                break

    @property
    def size(self):
        """Return the size of the cache"""
        return len(self.cache)


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
    _cacheManager = None

    def __init__(self, storage=None):
        ConfigurationManagerSingleton.__init__(self)
        if self._storage is None:
            if not isinstance(storage, StorageClientAsync):
                raise TypeError('Must be a valid Storage object')
            self._storage = storage
        if self._registered_interests is None:
            self._registered_interests = {}
        if self._cacheManager is None:
            self._cacheManager = ConfigurationCache()

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

    async def _merge_category_vals(self, category_val_new, category_val_storage, keep_original_items, category_name=None):
        # preserve all value_vals from category_val_storage
        # use items in category_val_new not in category_val_storage
        # keep_original_items = FALSE ignore items in category_val_storage not in category_val_new
        # keep_original_items = TRUE keep items in category_val_storage not in category_val_new
        category_val_storage_copy = copy.deepcopy(category_val_storage)
        category_val_new_copy = copy.deepcopy(category_val_new)
        deprecated_items = []
        for item_name_new, item_val_new in category_val_new_copy.items():
            item_val_storage = category_val_storage_copy.get(item_name_new)
            if item_val_storage is not None:
                for o_attr in item_val_storage.keys():
                    # Merge optional attributes
                    if o_attr in _optional_items:
                        item_val_new[o_attr] = item_val_storage.get(o_attr)
                item_val_new['value'] = item_val_storage.get('value')
                category_val_storage_copy.pop(item_name_new)
            if "deprecated" in item_val_new and item_val_new['deprecated'] == 'true':
                audit = AuditLogger(self._storage)
                audit_details = {'category': category_name, 'item': item_name_new, 'oldValue': item_val_new['value'],
                                 'newValue': 'deprecated'}
                await audit.information('CONCH', audit_details)
                deprecated_items.append(item_name_new)

        for item in deprecated_items:
            category_val_new_copy.pop(item)

        if keep_original_items:
            for item_name_storage, item_val_storage in category_val_storage_copy.items():
                category_val_new_copy[item_name_storage] = item_val_storage

        return category_val_new_copy

    async def _validate_category_val(self, category_name, category_val, set_value_val_from_default_val=True):
        require_entry_value = not set_value_val_from_default_val
        if type(category_val) is not dict:
            raise TypeError('For {} category, category value must be a dictionary; got {}'
                            .format(category_name, type(category_val)))
        category_val_copy = copy.deepcopy(category_val)
        for item_name, item_val in category_val_copy.items():
            if type(item_name) is not str:
                raise TypeError('For {} category, item name {} must be a string; got {}'
                                .format(category_name, item_name, type(item_name)))
            if type(item_val) is not dict:
                raise TypeError('For {} category, item value must be a dict for item name {}; got {}'
                                .format(category_name, item_name, type(item_val)))

            optional_item_entries = {'readonly': 0, 'order': 0, 'length': 0, 'maximum': 0, 'minimum': 0,
                                     'deprecated': 0, 'displayName': 0, 'rule': 0, 'validity': 0, 'mandatory': 0}
            expected_item_entries = {'description': 0, 'default': 0, 'type': 0}

            if require_entry_value:
                expected_item_entries['value'] = 0

            def get_entry_val(k):
                v = [val for name, val in item_val.items() if name == k]
                return v[0]

            for entry_name, entry_val in item_val.copy().items():
                if type(entry_name) is not str:
                    raise TypeError('For {} category, entry name {} must be a string for item name {}; got {}'
                                    .format(category_name, entry_name, item_name, type(entry_name)))

                # Validate enumeration type and mandatory options item_name
                if 'type' in item_val and get_entry_val("type") == 'enumeration':
                    if 'options' not in item_val:
                        raise KeyError('For {} category, options required for enumeration type'.format(category_name))
                    if entry_name == 'options':
                        if type(entry_val) is not list:
                            raise TypeError('For {} category, entry value must be a list for item name {} and '
                                            'entry name {}; got {}'.format(category_name, item_name, entry_name, type(entry_val)))
                        if not entry_val:
                            raise ValueError('For {} category, entry value cannot be empty list for item_name {} and '
                                             'entry_name {}; got {}'.format(category_name, item_name, entry_name, entry_val))
                        if get_entry_val("default") not in entry_val:
                            raise ValueError('For {} category, entry value does not exist in options list for item name'
                                             ' {} and entry_name {}; got {}'.format(category_name, item_name, entry_name, get_entry_val("default")))
                        else:
                            d = {entry_name: entry_val}
                            expected_item_entries.update(d)
                    else:
                        if type(entry_val) is not str:
                            raise TypeError('For {} category, entry value must be a string for item name {} and '
                                            'entry name {}; got {}'.format(category_name, item_name, entry_name, type(entry_val)))
                else:
                    if type(entry_val) is not str:
                        raise TypeError('For {} category, entry value must be a string for item name {} and '
                                        'entry name {}; got {}'.format(category_name, item_name, entry_name, type(entry_val)))

                # If Entry item exists in optional list, then update expected item entries
                if entry_name in optional_item_entries:
                    if entry_name == 'readonly' or entry_name == 'deprecated' or entry_name == 'mandatory':
                        if self._validate_type_value('boolean', entry_val) is False:
                            raise ValueError('For {} category, entry value must be boolean for item name {}; got {}'
                                             .format(category_name, entry_name, type(entry_val)))
                        else:
                            if entry_name == 'mandatory' and entry_val == 'true':
                                if not len(item_val['default'].strip()):
                                    raise ValueError('For {} category, A default value must be given for {}'.format(category_name, item_name))
                    elif entry_name == 'minimum' or entry_name == 'maximum':
                        if (self._validate_type_value('integer', entry_val) or self._validate_type_value('float', entry_val)) is False:
                            raise ValueError('For {} category, entry value must be an integer or float for item name '
                                             '{}; got {}'.format(category_name, entry_name, type(entry_val)))
                    elif entry_name == 'rule' or entry_name == 'displayName' or entry_name == 'validity':
                        if not isinstance(entry_val, str):
                            raise ValueError('For {} category, entry value must be string for item name {}; got {}'
                                             .format(category_name, entry_name, type(entry_val)))
                    else:
                        if self._validate_type_value('integer', entry_val) is False:
                            raise ValueError('For {} category, entry value must be an integer for item name {}; got {}'
                                             .format(category_name, entry_name, type(entry_val)))

                    d = {entry_name: entry_val}
                    expected_item_entries.update(d)
                num_entries = expected_item_entries.get(entry_name)
                if set_value_val_from_default_val and entry_name == 'value':
                    raise ValueError('Specifying value_name and value_val for item_name {} is not allowed if '
                                     'desired behavior is to use default_val as value_val'.format(item_name))
                if num_entries is None:
                    _logger.warning('For {} category, DISCARDING unrecognized entry name {} for item name {}'
                                    .format(category_name, entry_name, item_name))
                    try:
                        del category_val_copy[item_name][entry_name]
                    except Exception:
                            raise KeyError

                if entry_name == 'type':
                    if entry_val not in _valid_type_strings:
                        raise ValueError('For {} category, invalid entry value for entry name "type" for item name {}.'
                                         ' valid type strings are: {}'.format(category_name, item_name, _valid_type_strings))
                expected_item_entries[entry_name] = 1
            for needed_key, needed_value in expected_item_entries.items():
                if needed_value == 0:
                    raise ValueError('For {} category, missing entry name {} for item name {}'.format(
                        category_name, needed_key, item_name))

            # validate data type value
            if self._validate_type_value(get_entry_val("type"), get_entry_val("default")) is False:
                raise ValueError('For {} category, unrecognized value for item name {}'.format(category_name, item_name))
            if 'readonly' in item_val:
                item_val['readonly'] = self._clean('boolean', item_val['readonly'])
            if 'deprecated' in item_val:
                item_val['deprecated'] = self._clean('boolean', item_val['deprecated'])
            if 'mandatory' in item_val:
                item_val['mandatory'] = self._clean('boolean', item_val['mandatory'])

            if set_value_val_from_default_val:
                item_val['default'] = self._clean(item_val['type'], item_val['default'])
                item_val['value'] = item_val['default']
        return category_val_copy

    async def _create_new_category(self, category_name, category_val, category_description, display_name=None):
        try:
            if isinstance(category_val, dict):
                new_category_val = copy.deepcopy(category_val)
                # Remove "deprecated" items from a new category configuration
                for i, v in category_val.items():
                    if 'deprecated' in v and v['deprecated'] == 'true':
                        new_category_val.pop(i)
            else:
                new_category_val = category_val
            display_name = category_name if display_name is None else display_name
            audit = AuditLogger(self._storage)
            await audit.information('CONAD', {'name': category_name, 'category': new_category_val})
            payload = PayloadBuilder().INSERT(key=category_name, description=category_description,
                                              value=new_category_val, display_name=display_name).payload()
            result = await self._storage.insert_into_tbl("configuration", payload)
            response = result['response']
            self._cacheManager.update(category_name, category_description, new_category_val, display_name)
        except KeyError:
            raise ValueError(result['message'])
        except StorageServerError as ex:
            err_response = ex.error
            raise ValueError(err_response)

    async def _read_all_category_names(self):
        # SELECT configuration.key, configuration.description, configuration.value, configuration.display_name, configuration.ts FROM configuration
        payload = PayloadBuilder().SELECT("key", "description", "value", "display_name", "ts") \
            .ALIAS("return", ("ts", 'timestamp')) \
            .FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")).payload()
        results = await self._storage.query_tbl_with_payload('configuration', payload)

        category_info = []
        for row in results['rows']:
            category_info.append((row['key'], row['description'], row["display_name"]))
        return category_info

    async def _read_category(self, cat_name):
        # SELECT configuration.key, configuration.description, configuration.value, configuration.display_name, configuration.ts FROM configuration
        payload = PayloadBuilder().SELECT("key", "description", "value", "display_name", "ts") \
            .ALIAS("return", ("ts", 'timestamp')) \
            .FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")).WHERE(["key", "=", cat_name]).LIMIT(1).payload()
        result = await self._storage.query_tbl_with_payload('configuration', payload)
        return result['rows'][0] if result['rows'] else None

    async def _read_all_groups(self, root, children):
        async def nested_children(child):
            # Recursively find children
            if not child:
                return
            next_children = await self.get_category_child(child["key"])
            if len(next_children) == 0:
                child.update({"children": []})
            else:
                child.update({"children": next_children})
                # call for each child
                for next_child in child["children"]:
                    await nested_children(next_child)

        # SELECT key, description, display_name FROM configuration
        payload = PayloadBuilder().SELECT("key", "description", "display_name").payload()
        all_categories = await self._storage.query_tbl_with_payload('configuration', payload)

        # SELECT DISTINCT child FROM category_children
        unique_category_children_payload = PayloadBuilder().SELECT("child").DISTINCT(["child"]).payload()
        unique_category_children = await self._storage.query_tbl_with_payload('category_children', unique_category_children_payload)

        list_child = [row['child'] for row in unique_category_children['rows']]
        list_root = []
        list_not_root = []

        for row in all_categories['rows']:
            if row["key"] in list_child:
                list_not_root.append((row["key"], row["description"], row["display_name"]))
            else:
                list_root.append((row["key"], row["description"], row["display_name"]))
        if children:
            tree = []
            for k, v, d in list_root if root is True else list_not_root:
                tree.append({"key": k, "description": v, "displayName": d, "children": []})

            for branch in tree:
                await nested_children(branch)

            return tree

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
        # FROM fledge.configuration WHERE configuration.key='SENSORS'
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
        # FROM fledge.configuration WHERE configuration.key='PURGE_READ'
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
            # UPDATE fledge.configuration
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

    async def update_configuration_item_bulk(self, category_name, config_item_list):
        """ Bulk update config items

        Args:
            category_name: category name
            config_item_list: dict containing config item values

        Returns:
            None
        """

        try:
            payload = {"updates": []}
            audit_details = {'category': category_name, 'items': {}}
            cat_info = await self.get_category_all_items(category_name)
            if cat_info is None:
                raise NameError("No such Category found for {}".format(category_name))
            for item_name, new_val in config_item_list.items():
                if item_name not in cat_info:
                    raise KeyError('{} config item not found'.format(item_name))
                # Evaluate new_val as per rule if defined
                if 'rule' in cat_info[item_name]:
                    rule = cat_info[item_name]['rule'].replace("value", new_val)
                    if eval(rule) is False:
                        raise ValueError('The value of {} is not valid, please supply a valid value'.format(item_name))
                if cat_info[item_name]['type'] == 'JSON':
                    if isinstance(new_val, dict):
                        pass
                    elif not isinstance(new_val, str):
                        raise TypeError('new value should be a valid dict Or a string literal, in double quotes')
                elif not isinstance(new_val, str):
                    raise TypeError('new value should be of type string')

                if cat_info[item_name]['type'] == 'enumeration':
                    if new_val == '':
                        raise ValueError('entry_val cannot be empty')
                    if new_val not in cat_info[item_name]['options']:
                        raise ValueError('new value does not exist in options enum')
                else:
                    if self._validate_type_value(cat_info[item_name]['type'], new_val) is False:
                        raise TypeError('Unrecognized value name for item_name {}'.format(item_name))

                if 'mandatory' in cat_info[item_name]:
                    if cat_info[item_name]['mandatory'] == 'true':
                        if cat_info[item_name]['type'] == 'JSON':
                            if not len(new_val):
                                raise ValueError("Dict cannot be set as empty. A value must be given for {}".format(item_name))
                        elif not len(new_val.strip()):
                            raise ValueError("A value must be given for {}".format(item_name))
                old_value = cat_info[item_name]['value']
                new_val = self._clean(cat_info[item_name]['type'], new_val)
                # Validations on the basis of optional attributes
                self._validate_value_per_optional_attribute(item_name, cat_info[item_name], new_val)

                old_value_for_check = old_value
                new_val_for_check = new_val
                if type(new_val) == dict:
                    # it converts .old so both .new and .old are dicts
                    # it uses OrderedDict to preserve the sequence of the keys
                    try:
                        old_value_dict = ast.literal_eval(old_value)
                        old_value_for_check = collections.OrderedDict(old_value_dict)
                        new_val_for_check = collections.OrderedDict(new_val)
                    except:
                        old_value_for_check = old_value
                        new_val_for_check = new_val

                if old_value_for_check != new_val_for_check:
                    payload_item = PayloadBuilder().SELECT("key", "description", "ts", "value") \
                        .JSON_PROPERTY(("value", [item_name, "value"], new_val)) \
                        .FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")) \
                        .WHERE(["key", "=", category_name]).payload()
                    payload['updates'].append(json.loads(payload_item))
                    audit_details['items'].update({item_name: {'oldValue': old_value, 'newValue': new_val}})

            if not payload['updates']:
                return
            
            await self._storage.update_tbl("configuration", json.dumps(payload))

            # read the updated value from storage
            cat_value = await self._read_category_val(category_name)
            # Category config items cache updated
            for item_name, new_val in config_item_list.items():
                if category_name in self._cacheManager.cache:
                    if item_name in self._cacheManager.cache[category_name]['value']:
                        self._cacheManager.cache[category_name]['value'][item_name]['value'] = cat_value[item_name]['value']
                    else:
                        self._cacheManager.cache[category_name]['value'].update({item_name: cat_value[item_name]['value']})

            # Configuration Change audit entry
            audit = AuditLogger(self._storage)
            await audit.information('CONCH', audit_details)
        except Exception as ex:
            _logger.exception('Unable to bulk update config items %s', str(ex))
            raise

        try:
            await self._run_callbacks(category_name)
        except:
            _logger.exception(
                'Unable to run callbacks for category_name %s', category_name)
            raise

    async def _update_category(self, category_name, category_val, category_description, display_name=None):
        try:
            display_name = category_name if display_name is None else display_name
            payload = PayloadBuilder().SET(value=category_val, description=category_description, display_name=display_name).WHERE(["key", "=", category_name]).payload()
            result = await self._storage.update_tbl("configuration", payload)
            response = result['response']
            # Re-read category from DB
            new_category_val_db = await self._read_category_val(category_name)
            if category_name in self._cacheManager.cache:
                self._cacheManager.cache[category_name]['description'] = category_description
                self._cacheManager.cache[category_name]['value'] = new_category_val_db
                self._cacheManager.cache[category_name]['displayName'] = display_name
            else:
                self._cacheManager.cache.update({category_name: {"description": category_description,
                                                                 "value": new_category_val_db,
                                                                 "displayName": display_name}})
        except KeyError:
            raise ValueError(result['message'])
        except StorageServerError as ex:
            err_response = ex.error
            raise ValueError(err_response)

    async def get_all_category_names(self, root=None, children=False):
        """Get all category names in the Fledge system

        Args:
            root: If true then select all keys from categories table and then filter out
                  that are children of another category. So the root categories are those
                  entries in configuration table that do not appear in distinct child in category_children
                  If false then it will return distinct child in category_children
                  If root is None then it will return all categories
            children: If true then it will return nested array of children of that category
                      If false then it will return categories on the basis of root value
        Return Values:
                    a list of tuples (string category_name, string category_description)
        """
        try:
            info = await self._read_all_groups(root, children) if root is not None else await self._read_all_category_names()
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
            if category_name in self._cacheManager:
                # Interim solution; to ensure script type config item file content handling
                category_value = self._handle_script_type(category_name, self._cacheManager.cache[category_name]['value'])
                self._cacheManager.update(category_name, self._cacheManager.cache[category_name]['description'],
                                          category_value, self._cacheManager.cache[category_name]['displayName'])
                return category_value

            category = await self._read_category(category_name)  # await self._read_category_val(category_name)
            category_value = None
            if category is not None:
                category_value = self._handle_script_type(category_name, category["value"])
                self._cacheManager.update(category_name, category["description"], category_value,
                                          category["display_name"])
            return category_value
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
            if category_name in self._cacheManager:
                if item_name not in self._cacheManager.cache[category_name]['value']:
                    return None
                return self._cacheManager.cache[category_name]['value'][item_name]
            else:
                cat_item = await self._read_item_val(category_name, item_name)
                if cat_item is not None:
                    category = await self._read_category(category_name)  # await self._read_category_val(category_name)
                    if category is not None:
                        category_value = self._handle_script_type(category_name, category["value"])
                        self._cacheManager.update(category_name, category["description"], category_value,
                                                  category["display_name"])
                        cat_item = category_value[item_name]
                return cat_item
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

    async def set_category_item_value_entry(self, category_name, item_name, new_value_entry, script_file_path=""):
        """Set the "value" entry of a given item within a given category.

        Keyword Arguments:
        category_name -- name of the category (required)
        item_name -- name of item within the category whose "value" entry needs to be changed (required)
        new_value_entry -- new value entry to replace old value entry
        script_file_path -- Script file path for the config item whose type is script

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
            storage_value_entry = None
            if category_name in self._cacheManager:
                if item_name not in self._cacheManager.cache[category_name]['value']:
                    raise ValueError("No detail found for the category_name: {} and item_name: {}"
                                     .format(category_name, item_name))
                storage_value_entry = self._cacheManager.cache[category_name]['value'][item_name]

                if storage_value_entry['value'] == new_value_entry:
                    return
            else:
                # get storage_value_entry and compare against new_value_value with its type, update if different
                storage_value_entry = await self._read_item_val(category_name, item_name)
                # check for category_name and item_name combination existence in storage
                if storage_value_entry is None:
                    raise ValueError("No detail found for the category_name: {} and item_name: {}"
                                     .format(category_name, item_name))
                if storage_value_entry == new_value_entry:
                    return

            # Special case for enumeration field type handling
            if storage_value_entry['type'] == 'enumeration':
                if new_value_entry == '':
                    raise ValueError('entry_val cannot be empty')
                if new_value_entry not in storage_value_entry['options']:
                    raise ValueError('new value does not exist in options enum')
            else:
                if self._validate_type_value(storage_value_entry['type'], new_value_entry) is False:
                    raise TypeError('Unrecognized value name for item_name {}'.format(item_name))
            if 'mandatory' in storage_value_entry:
                if storage_value_entry['mandatory'] == 'true':
                    if storage_value_entry['type'] != 'JSON' and not len(new_value_entry.strip()):
                        raise ValueError("A value must be given for {}".format(item_name))
                    elif storage_value_entry['type'] == 'JSON' and not len(new_value_entry):
                        raise ValueError("Dict cannot be set as empty. A value must be given for {}".format(item_name))
            new_value_entry = self._clean(storage_value_entry['type'], new_value_entry)
            # Evaluate new_value_entry as per rule if defined
            if 'rule' in storage_value_entry:
                rule = storage_value_entry['rule'].replace("value", new_value_entry)
                if eval(rule) is False:
                    raise ValueError('The value of {} is not valid, please supply a valid value'.format(item_name))
            # Validations on the basis of optional attributes
            self._validate_value_per_optional_attribute(item_name, storage_value_entry, new_value_entry)

            await self._update_value_val(category_name, item_name, new_value_entry)
            # always get value from storage
            cat_item = await self._read_item_val(category_name, item_name)
            # Special case for script type
            if storage_value_entry['type'] == 'script':
                if cat_item['value'] is not None and cat_item['value'] != "":
                    cat_item["value"] = binascii.unhexlify(cat_item['value'].encode('utf-8')).decode("utf-8")
                cat_item["file"] = script_file_path

            if category_name in self._cacheManager.cache:
                if item_name in self._cacheManager.cache[category_name]['value']:
                    self._cacheManager.cache[category_name]['value'][item_name]['value'] = cat_item['value']
                    if storage_value_entry['type'] == 'script':
                        self._cacheManager.cache[category_name]['value'][item_name]["file"] = script_file_path
                else:
                    self._cacheManager.cache[category_name]['value'].update({item_name: cat_item['value']})
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

    async def set_optional_value_entry(self, category_name, item_name, optional_entry_name, new_value_entry):
        """Set the "optional_key" entry of a given item within a given category.
        Even we can reset the optional value by just passing new_value_entry=""

        Keyword Arguments:
        category_name -- name of the category (required)
        item_name -- name of item within the category whose "optional_key" entry needs to be changed (required)
        optional_entry_name -- name of the optional attribute
        new_value_entry -- new value entry to replace old value entry

        Return Values:
        None
        """
        try:
            storage_value_entry = None
            if category_name in self._cacheManager:
                if item_name not in self._cacheManager.cache[category_name]['value']:
                    raise ValueError("No detail found for the category_name: {} and item_name: {}"
                                     .format(category_name, item_name))
                storage_value_entry = self._cacheManager.cache[category_name]['value'][item_name]
                if optional_entry_name not in storage_value_entry:
                    raise KeyError("{} does not exist".format(optional_entry_name))
                if storage_value_entry[optional_entry_name] == new_value_entry:
                    return
            else:
                # get storage_value_entry and compare against new_value_value with its type, update if different
                storage_value_entry = await self._read_item_val(category_name, item_name)
                # check for category_name and item_name combination existence in storage
                if storage_value_entry is None:
                    raise ValueError("No detail found for the category_name: {} and item_name: {}"
                                     .format(category_name, item_name))
                if storage_value_entry[optional_entry_name] == new_value_entry:
                    return
            # Validate optional types only when new_value_entry not empty; otherwise set empty value
            if new_value_entry:
                if optional_entry_name == 'readonly' or optional_entry_name == 'deprecated' or optional_entry_name == 'mandatory':
                    if self._validate_type_value('boolean', new_value_entry) is False:
                        raise ValueError('For {} category, entry value must be boolean for optional item name {}; got {}'
                                         .format(category_name, optional_entry_name, type(new_value_entry)))
                elif optional_entry_name == 'minimum' or optional_entry_name == 'maximum':
                    if (self._validate_type_value('integer', new_value_entry) or self._validate_type_value('float', new_value_entry)) is False:
                        raise ValueError('For {} category, entry value must be an integer or float for optional item '
                                         '{}; got {}'.format(category_name, optional_entry_name, type(new_value_entry)))
                elif optional_entry_name == 'rule' or optional_entry_name == 'displayName' or optional_entry_name == 'validity':
                    if not isinstance(new_value_entry, str):
                        raise ValueError('For {} category, entry value must be string for optional item {}; got {}'
                                         .format(category_name, optional_entry_name, type(new_value_entry)))
                else:
                    if self._validate_type_value('integer', new_value_entry) is False:
                        raise ValueError('For {} category, entry value must be an integer for optional item {}; got {}'
                                         .format(category_name, optional_entry_name, type(new_value_entry)))

                # Validation is fairly minimal, minimum, maximum like
                # maximum should be greater than minimum or vice-versa
                # And no link between minimum, maximum and length is needed.
                # condition check with numeric operands (int or float) rather than with string operands
                def convert(value, _type):
                    return int(value) if _type == "integer" else float(value) if _type == "float" else value

                if optional_entry_name == 'minimum':
                    new = convert(new_value_entry, storage_value_entry['type'])
                    old = convert(storage_value_entry['maximum'], storage_value_entry['type'])
                    if new > old:
                        raise ValueError('Minimum value should be less than equal to Maximum value')

                if optional_entry_name == 'maximum':
                    new = convert(new_value_entry, storage_value_entry['type'])
                    old = convert(storage_value_entry['minimum'], storage_value_entry['type'])
                    if new < old:
                        raise ValueError('Maximum value should be greater than equal to Minimum value')
            payload = PayloadBuilder().SELECT("key", "description", "ts", "value") \
                .JSON_PROPERTY(("value", [item_name, optional_entry_name], new_value_entry)) \
                .FORMAT("return", ("ts", "YYYY-MM-DD HH24:MI:SS.MS")) \
                .WHERE(["key", "=", category_name]).payload()
            await self._storage.update_tbl("configuration", payload)
            # always get value from storage
            cat_item = await self._read_item_val(category_name, item_name)
            if category_name in self._cacheManager.cache:
                if item_name in self._cacheManager.cache[category_name]['value']:
                    self._cacheManager.cache[category_name]['value'][item_name][optional_entry_name] = cat_item[optional_entry_name]
                else:
                    self._cacheManager.cache[category_name]['value'].update({item_name: cat_item[optional_entry_name]})
        except:
            _logger.exception(
                'Unable to set optional %s entry based on category_name %s and item_name %s and value_item_entry %s', optional_entry_name, category_name, item_name, new_value_entry)
            raise

    async def create_category(self, category_name, category_value, category_description='', keep_original_items=False, display_name=None):
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
        display_name -- configuration category for display in the GUI. if it is NONE then use the value of the category_name

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
        A Fledge component calls this method to create one or more new configuration categories to store initial configuration.
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
            category_val_prepared = await self._validate_category_val(category_name, category_value, True)
            # Evaluate value as per rule if defined
            for item_name in category_val_prepared:
                if 'rule' in category_val_prepared[item_name]:
                    rule = category_val_prepared[item_name]['rule'].replace("value", category_val_prepared[item_name]['value'])
                    if eval(rule) is False:
                        raise ValueError('For {} category, The value of {} is not valid, please supply a valid value'.format(category_name, item_name))
            # check if category_name is already in storage
            category_val_storage = await self._read_category_val(category_name)
            if category_val_storage is None:
                await self._create_new_category(category_name, category_val_prepared, category_description, display_name)
            else:
                # validate category_val from storage, do not set "value" from default, reuse from storage value
                try:
                    category_val_storage = await self._validate_category_val(category_name, category_val_storage, False)
                # if validating category from storage fails, nothing to salvage from storage, use new completely
                except:
                    _logger.exception(
                        'category_value for category_name %s from storage is corrupted; using category_value without merge',
                        category_name)
                # if validating category from storage succeeds, merge new and storage
                else:
                    all_categories = await self._read_all_category_names()
                    for c in all_categories:
                        if c[0] == category_name:
                            display_name_storage = c[2]
                            break
                    if display_name is None:
                        display_name = display_name_storage

                    category_val_prepared = await self._merge_category_vals(category_val_prepared, category_val_storage,
                                                                            keep_original_items, category_name)
                    if json.dumps(category_val_prepared, sort_keys=True) == json.dumps(category_val_storage,
                                                                                       sort_keys=True):
                        if display_name_storage == display_name:
                            return

                        await self._update_category(category_name, category_val_prepared, category_description, display_name)
                    else:
                        await self._update_category(category_name, category_val_prepared, category_description, display_name)
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
            payload = PayloadBuilder().SELECT("key", "description", "display_name").WHERE(["key", "=", item['child']]).payload()
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
            children = await self._read_child_info(child_cat_names)
            return [{"key": c['key'], "description": c['description'], "displayName": c['display_name']} for c in children]
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

    async def delete_category_and_children_recursively(self, category_name):
        """Delete recursively a category and its children along with their parent-child relationship
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
        catg_descendents = await self._fetch_descendents(category_name)

        for catg in RESERVED_CATG:
            if catg in catg_descendents:
                raise ValueError('Reserved category found in descendents of {} - {}'.format(category_name, catg_descendents))
        try:
            result = await self._delete_recursively(category_name)
        except ValueError as ex:
            raise ValueError(ex)
        else:
            return result[category_name]

    async def _fetch_descendents(self, cat):
        children = await self._read_all_child_category_names(cat)
        descendents = []
        for row in children:
            child = row['child']
            descendents.append(child)
            child_descendents = await self._fetch_descendents(child)
            descendents.extend(child_descendents)
        return descendents

    async def _delete_recursively(self, cat):
        try:
            children = await self._read_all_child_category_names(cat)
            for row in children:
                child = row['child']
                await self._delete_recursively(child)

            # Remove cat as child from parent-child relation.
            payload = PayloadBuilder().WHERE(["child", "=", cat]).payload()
            result = await self._storage.delete_from_tbl("category_children", payload)
            if result['response'] == 'deleted':
                _logger.info('Deleted parent in category_children: %s', cat)

            # Remove category.
            payload = PayloadBuilder().WHERE(["key", "=", cat]).payload()
            result = await self._storage.delete_from_tbl("configuration", payload)
            if result['response'] == 'deleted':
                _logger.info('Deleted parent category from configuration: %s', cat)
                audit = AuditLogger(self._storage)
                audit_details = {'categoryDeleted': cat}
                # FIXME: FOGL-2140
                await audit.information('CONCH', audit_details)

            # delete_category_script_files is a better name in today's context. But in future there can be more stuff
            #  related to the category; the definition of method should be extended as required
            self.delete_category_related_things(cat)

            # Remove cat from cache
            if cat in self._cacheManager.cache:
                self._cacheManager.remove(cat)

        except KeyError as ex:
            raise ValueError(ex)
        except StorageServerError as ex:
            err_response = ex.error
            raise ValueError(err_response)
        else:
            return {cat: result}

    def delete_category_related_things(self, category_name):
        """ On delete category request

        - Delete category related files

        :param category_name:
        :return:
        """
        import glob
        uploaded_scripts_dir = '{}/data/scripts/'.format(_FLEDGE_ROOT)
        if _FLEDGE_DATA:
            uploaded_scripts_dir = '{}/scripts/'.format(_FLEDGE_DATA)
        files = "{}/{}_*".format(uploaded_scripts_dir, category_name.lower())
        try:
            for f in glob.glob(files):
                _logger.info("Removing file %s for category %s", f, category_name)
                os.remove(f)
        except Exception as ex:
            _logger.error('Failed to delete file(s) for category %s. Exception %s', category_name, str(ex))
            # raise ex

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
        For example, if a callback is 'fledge.callback', then user must implement fledge/callback.py module with method run(category_name).
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

        def _str_to_float(item_val):
            try:
                _value = float(item_val)
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
        elif _type == 'float':
            return _str_to_float(_value)
        elif _type == 'JSON':
            if isinstance(_value, dict):
                return True
            return Utils.is_json(_value)
        elif _type == 'IPv4' or _type == 'IPv6':
            return _str_to_ipaddress(_value)
        elif _type == 'URL':
            try:
                result = urlparse(_value)
                return True if all([result.scheme, result.netloc]) else False
            except:
                return False
        elif _type == 'string' or _type == 'northTask':
            return isinstance(_value, str)

    def _clean(self, item_type, item_val):
        if item_type == 'boolean':
            return item_val.lower()
        elif item_type == 'float':
            return str(float(item_val))

        return item_val

    def _handle_script_type(self, category_name, category_value):
        """For the given category, check for config item of type script “unhexlify” the value stored in database
        and add “file” attribute on the fly

        Keyword Arguments:
        category_name -- name of the category
        category_value -- category value

        Return Values:
        JSON
        """
        import glob
        cat_value = copy.deepcopy(category_value)
        for k, v in cat_value.items():
            if v['type'] == 'script':
                try:
                    # cat_value[k]["file"] = ""
                    if v['value'] is not None and v['value'] != "":
                        cat_value[k]["value"] = binascii.unhexlify(v['value'].encode('utf-8')).decode("utf-8")
                except binascii.Error:
                    pass
                except Exception as e:
                    _logger.warning(
                        "Got an issue while decoding config item: {} | {}".format(cat_value[k], str(e)))
                    pass

                script_dir = _FLEDGE_DATA + '/scripts/' if _FLEDGE_DATA else _FLEDGE_ROOT + "/data/scripts/"
                prefix_file_name = category_name.lower() + "_" + k.lower() + "_"
                if not os.path.exists(script_dir):
                    os.makedirs(script_dir)
                else:
                    # find pattern with file_name
                    list_of_files = glob.glob(script_dir + prefix_file_name + "*.py")
                    if list_of_files:
                        # get latest modified file
                        latest_file = max(list_of_files, key=os.path.getmtime)
                        cat_value[k]["file"] = latest_file
        return cat_value

    def _validate_value_per_optional_attribute(self, item_name, storage_value_entry, new_value_entry):
        # FIXME: Logically below exception throw as ValueError; TypeError used ONLY to get right HTTP status code returned from API endpoint.
        # As we used same defs for optional attribute value & config item value save
        def in_range(n, start, end):
            return start <= n <= end  # start and end inclusive

        config_item_type = storage_value_entry['type']
        if config_item_type == 'string':
            if 'length' in storage_value_entry:
                if len(new_value_entry) > int(storage_value_entry['length']):
                    raise TypeError('For config item {} you cannot set the new value, beyond the length {}'.format(
                        item_name, storage_value_entry['length']))

        if config_item_type == 'integer' or config_item_type == 'float':
            if 'minimum' in storage_value_entry and 'maximum' in storage_value_entry:
                if config_item_type == 'integer':
                    _new_value = int(new_value_entry)
                    _min_value = int(storage_value_entry['minimum'])
                    _max_value = int(storage_value_entry['maximum'])
                else:
                    _new_value = float(new_value_entry)
                    _min_value = float(storage_value_entry['minimum'])
                    _max_value = float(storage_value_entry['maximum'])

                if not in_range(_new_value, _min_value, _max_value):
                    raise TypeError('For config item {} you cannot set the new value, beyond the range ({},{})'.format(
                        item_name, storage_value_entry['minimum'], storage_value_entry['maximum']))
            elif 'minimum' in storage_value_entry:
                if config_item_type == 'integer':
                    _new_value = int(new_value_entry)
                    _min_value = int(storage_value_entry['minimum'])
                else:
                    _new_value = float(new_value_entry)
                    _min_value = float(storage_value_entry['minimum'])
                if _new_value < _min_value:
                    raise TypeError('For config item {} you cannot set the new value, below {}'.format(item_name,
                                                                                                       _min_value))
            elif 'maximum' in storage_value_entry:
                if config_item_type == 'integer':
                    _new_value = int(new_value_entry)
                    _max_value = int(storage_value_entry['maximum'])
                else:
                    _new_value = float(new_value_entry)
                    _max_value = float(storage_value_entry['maximum'])
                if _new_value > _max_value:
                    raise TypeError('For config item {} you cannot set the new value, above {}'.format(item_name,
                                                                                                       _max_value))
