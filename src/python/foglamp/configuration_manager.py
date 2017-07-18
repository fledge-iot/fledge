# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Configuration Manager """

import logging
import aiopg.sa
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import text

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_configuration_tbl = sa.Table(
    'configuration',
    sa.MetaData(),
    sa.Column('key', sa.types.CHAR(10)),
    sa.Column('description', sa.types.VARCHAR(255)),
    sa.Column('value', JSONB),
    sa.Column('ts', sa.types.TIMESTAMP)
)
"""Defines the table that data will be used for CRUD operations"""

_valid_type_strings = ['boolean', 'integer', 'string', 'IPv4', 'IPv6', 'X509 certificate', 'password']
_connection_string = 'postgresql://foglamp:foglamp@localhost:5432/foglamp'
_logger = logging.getLogger(__name__)

"""
General naming convention:
category(s)
	category_name - string
	category_description - string
	category_val - dict
		item_name - string (dynamic)
		item_val - dict
		    entry_name - string
		    entry_val - string
-----------4 fixed entry_name/entry_val pairs-------------------------
            description_name - string (fixed - 'description')
                description_val - string (dynamic)
            type_name - string (fixed - 'type')
                type_val - string (dynamic - ('boolean', 'integer', 'string', 'IPv4', 'IPv6', 'X509 certificate'))
            default_name - string (fixed - 'default')
                default_val - string (dynamic)
            value_name - string (fixed - 'value')
                value_val - string (dynamic)
"""


async def _merge_category_vals(category_val_new, category_val_storage):
    # preserve all value_vals from category_val_storage
    # use items in category_val_new not in category_val_storage
    # ignore items in category_val_storage not in category_val_new
    for item_name_new, item_val_new in category_val_new.items():
        item_val_storage = category_val_storage.get(item_name_new)
        if item_val_storage is not None:
            item_val_new['value'] = item_val_storage.get('value')
    return category_val_new


async def _validate_category_val(category_val, set_value_val_from_default_val=True):
    require_entry_value = not set_value_val_from_default_val
    if type(category_val) is not dict:
        raise TypeError('category_val must be a dictionary')
    for item_name, item_val in category_val.items():
        if type(item_name) is not str:
            raise TypeError('item_name must be a string')
        if type(item_val) is not dict:
            raise TypeError('item_value must be a dict for item_name {}'.format(item_name))
        expected_item_entries = {'description': 0, 'default': 0, 'type': 0}
        if require_entry_value:
            expected_item_entries['value'] = 0
        for entry_name, entry_val in item_val.items():
            if type(entry_name) is not str:
                raise TypeError('entry_name must be a string for item_name {}'.format(item_name))
            if type(entry_val) is not str:
                raise TypeError(
                    'entry_val must be a string for item_name {} and entry_name'.format(item_name, entry_name))
            num_entries = expected_item_entries.get(entry_name)
            if set_value_val_from_default_val and entry_name == 'value':
                raise ValueError(
                    'Specifying value_name and value_val for item_name {} is not allowed if desired behavior is to use default_val as value_val'.format(
                        item_name))
            if num_entries is None:
                raise ValueError('Unrecognized entry_name for item_name {}'.format(item_name))
            if num_entries > 0:
                raise ValueError('Duplicate entry_name for item_name {}'.format(item_name))
            if entry_name == 'type':
                if entry_val not in _valid_type_strings:
                    raise ValueError(
                        'Invalid entry_val for entry_name "type" for item_name {}. valid: {}'.format(item_name,
                                                                                                     _valid_type_strings))
            expected_item_entries[entry_name] = 1
        for needed_key, needed_value in expected_item_entries.items():
            if needed_value == 0:
                raise ValueError('Missing entry_name {} for item_name {}'.format(needed_key, item_name))
        if set_value_val_from_default_val:
            item_val['value'] = item_val['default']
    return category_val


async def _create_new_category(category_name, category_val, category_description):
    async with aiopg.sa.create_engine(_connection_string) as engine:
        async with engine.acquire() as conn:
            await conn.execute(_configuration_tbl.insert().values(key=category_name, value=category_val,
                                                                  description=category_description))


async def _read_all_category_names():
    async with aiopg.sa.create_engine(_connection_string) as engine:
        async with engine.acquire() as conn:
            category_info = []
            async for row in conn.execute(_configuration_tbl.select()):
                category_info.append((row.key, row.description))
            return category_info


async def _read_category_val(category_name):
    async with aiopg.sa.create_engine(_connection_string) as engine:
        async with engine.acquire() as conn:
            async for row in conn.execute(
                    _configuration_tbl.select().where(_configuration_tbl.c.key == category_name)):
                return row.value


async def _read_item_val(category_name, item_name):
    query_template = """
        SELECT 
            configuration.value::json->'{}' as value
        FROM 
            foglamp.configuration
        WHERE 
            configuration.key='{}'
    """
    query_full = query_template.format(item_name, category_name)
    async with aiopg.sa.create_engine(_connection_string) as engine:
        async with engine.acquire() as conn:
            async for row in conn.execute(text(query_full).columns(_configuration_tbl.c.value)):
                return row.value


async def _read_value_val(category_name, item_name):
    query_template = """
        SELECT 
            configuration.value::json->'{}'->'value' as value
        FROM 
            foglamp.configuration
        WHERE 
            configuration.key='{}'
    """
    query_full = query_template.format(item_name, category_name)
    async with aiopg.sa.create_engine(_connection_string) as engine:
        async with engine.acquire() as conn:
            async for row in conn.execute(text(query_full).columns(_configuration_tbl.c.value)):
                return row.value


async def _update_value_val(category_name, item_name, new_value_val):
    query_template = """
            UPDATE foglamp.configuration 
            SET value = jsonb_set(value, '{{{},value}}', '"{}"') 
            WHERE key='{}'
        """
    query_full = query_template.format(item_name, new_value_val, category_name)
    async with aiopg.sa.create_engine(_connection_string) as engine:
        async with engine.acquire() as conn:
            await conn.execute(query_full)


async def _update_category(category_name, category_val, category_description):
    async with aiopg.sa.create_engine(_connection_string) as engine:
        async with engine.acquire() as conn:
            await conn.execute(
                _configuration_tbl.update().where(_configuration_tbl.c.key == category_name).values(value=category_val,
                                                                                                    description=category_description))


async def get_all_category_names():
    """Get all category names in the FogLAMP system

    Return Values:
    a list of tuples (string category_name, string category_description)
    None
    """
    try:
        return await _read_all_category_names()
    except:
        _logger.exception(
            'Unable to read all category names')
        raise


async def get_category_all_items(category_name):
    """Get a specified category's entire configuration (all items).

    Keyword Arguments:
    category_name -- name of the category (required)

    Return Values:
    a JSONB dictionary with all items of a category's configuration
    None
    """
    try:
        return await _read_category_val(category_name)
    except:
        _logger.exception(
            'Unable to get all category names based on category_name %s', category_name)
        raise


async def get_category_item(category_name, item_name):
    """Get a given item within a given category.

    Keyword Arguments:
    category_name -- name of the category (required)
    item_name -- name of the item within the category (required)

    Return Values:
    a JSONB dictionary with item's content
    None
    """
    try:
        return await _read_item_val(category_name, item_name)
    except:
        _logger.exception(
            'Unable to get category item based on category_name %s and item_name %s', category_name, item_name)
        raise


async def get_category_item_value_entry(category_name, item_name):
    """Get the "value" entry of a given item within a given category.

    Keyword Arguments:
    category_name -- name of the category (required)
    item_name -- name of the item within the category (required)

    Return Values:
    a string of the "value" entry
    None
    """
    try:
        return await _read_value_val(category_name, item_name)
    except:
        _logger.exception(
            'Unable to get the "value" entry based on category_name %s and item_name %s', category_name,
            item_name)
        raise


async def set_category_item_value_entry(category_name, item_name, new_value_entry):
    """Set the "value" entry of a given item within a given category.

    Keyword Arguments:
    category_name -- name of the category (required)
    item_name -- name of item within the category whose "value" entry needs to be changed (required)
    new_value_entry -- new value entry to replace old value entry

    Return Values:
    None
    """
    try:
        return await _update_value_val(category_name, item_name, new_value_entry)
    except:
        _logger.exception(
            'Unable to set item value entry based on category_name %s and item_name %s and value_item_entry %s',
            category_name, item_name, new_value_entry)
        raise


async def create_category(category_name, category_value, category_description=''):
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

    Return Values:
    None

    Side Effects:
    A "value" entry will be created for each item using the "Default" entry's specified value.
    If a category of this name already exists within the storage, the new category_val and the storage's category_val will be merged such that:
        1. preserve all "value" entries from the storage's category val
        2. use items in the new category_val that are not in the storage's category_val
        3. ignore items in storage's category_val that are not in the new not in category_val

    Exceptions Raised:
    ValueError
    TypeError

    Restrictions and Usage:
    A FogLAMP component calls this method to create one or more new configuration categories to store initial configuration.
    Only default values can be entered for and item's entries.
    A "value" entry specified for an item will raise an exception.
    """
    category_val_prepared = ''
    try:
        # validate new category_val
        category_val_prepared = await _validate_category_val(category_value, True)
        # check if category_name is already in storage
        category_val_storage = await _read_category_val(category_name)
        if category_val_storage is None:
            return await _create_new_category(category_name, category_val_prepared, category_description)
        else:
            # validate category_val from storage
            try:
                category_val_storage = await _validate_category_val(category_val_storage, False)
            except:
                _logger.exception(
                    'category_value for category_name %s from storage is corrupted; using category_value without merge',
                    category_name)
            else:
                category_val_prepared = await _merge_category_vals(category_val_prepared, category_val_storage)
            return await _update_category(category_name, category_val_prepared, category_description)

    except:
        _logger.exception(
            'Unable to create new category based on category_name %s and category_description %s and category_json_schema %s',
            category_name, category_description, category_val_prepared)
        raise
    return None


def register_category(category_name, callback):
    pass

# async def main_test():
#     # lifecycle of a component's configuration
#     # start component
#     # 1. create a configuration that does not exist - use all default values
#     # 2. read the configuration back in (cache locally for reuse)
#     # update config while system is up
#     # 1. a user updates the "value" entry of an item to non-default value
#     #    (callback is not implemented to update/notify component once change to config is made)
#     # restart component
#     # 1. create/update a configuration that already exists (merge)
#     # 2. read the configuration back in (cache locally for reuse)
#
#
#     sample_json = {
#         "port": {
#             "description": "Port to listen on",
#             "default": "5683",
#             "type": "integer"
#         },
#         "url": {
#             "description": "URL to accept data on",
#             "default": "sensor/reading-values",
#             "type": "string"
#         },
#         "certificate": {
#             "description": "X509 certificate used to identify ingress interface",
#             "default": "47676565",
#             "type": "X509 certificate"
#         }
#     }
#
#     print("test create_category")
#     await create_category('CATEG', sample_json, 'CATEG_DESCRIPTION')
#
#     print("test get_all_category_names")
#     names_list = await get_all_category_names()
#     for row in names_list:
#         # tuple
#         print(row)
#
#     print("test get_category_all_items")
#     json = await get_category_all_items('CATEG')
#     print(json)
#     print(type(json))
#
#     print("test get_category_item")
#     json = await get_category_item('CATEG', "url")
#     print(json)
#     print(type(json))
#
#     print("test get_category_item_value")
#     string_result = await get_category_item_value_entry('CATEG', "url")
#     print(string_result)
#     print(type(string_result))
#
#     print("test set_category_item_value_entry")
#     await set_category_item_value_entry('CATEG', "url", "blablabla")
#
#     print("test get_category_item_value")
#     string_result = await get_category_item_value_entry('CATEG', "url")
#     print(string_result)
#     print(type(string_result))
#
#     print("test create_category second run. add port2, add url2, keep certificate, drop old port and old url")
#     sample_json = {
#         "port2": {
#             "description": "Port to listen on",
#             "default": "5683",
#             "type": "integer"
#         },
#         "url2": {
#             "description": "URL to accept data on",
#             "default": "sensor/reading-values",
#             "type": "string"
#         },
#         "certificate": {
#             "description": "X509 certificate used to identify ingress interface",
#             "default": "47676565",
#             "type": "X509 certificate"
#         }
#     }
#     await create_category('CATEG', sample_json, 'CATEG_DESCRIPTION')
#
#     print("test get_all_items")
#     json = await get_category_all_items('CATEG')
#     print(json)
#     print(type(json))
#
# if __name__ == '__main__':
#     import asyncio
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(main_test())
