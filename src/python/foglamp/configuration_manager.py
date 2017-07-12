# -*- coding: utf-8 -*-
"""FOGLAMP_PRELUDE_BEGIN
{{FOGLAMP_LICENSE_DESCRIPTION}}

See: http://foglamp.readthedocs.io/

Copyright (c) 2017 OSIsoft, LLC
License: Apache 2.0

FOGLAMP_PRELUDE_END
"""

import logging
import psycopg2
import aiopg.sa
import sqlalchemy as sa
import asyncio
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import text

"""Configuration Manager
"""

__author__ = 'Ashwin Gopalakrishnan'
__version__ = '${VERSION}'

_configuration_tbl = sa.Table(
    'configuration',
    sa.MetaData(),
    sa.Column('key', sa.types.CHAR(10)),
    sa.Column('description', sa.types.VARCHAR(255)),
    sa.Column('value', JSONB),
    sa.Column('ts', sa.types.TIMESTAMP)
)
"""Defines the table that data will be inserted into"""

_connection_string = 'postgresql://foglamp:foglamp@localhost:5432/foglamp'
_logger_name = 'configuration-manager'

async def _create_new_category(category_name, category_description, category_json_schema):
    async with aiopg.sa.create_engine(_connection_string) as engine:
        async with engine.acquire() as conn:
            await conn.execute(_configuration_tbl.insert().values(key=category_name, value=category_json_schema,
                                                                      description=category_description))

async def _read_all_category_keys():
    async with aiopg.sa.create_engine(_connection_string) as engine:
        async with engine.acquire() as conn:
            category_names = []
            async for row in conn.execute(_configuration_tbl.select()):
                category_names.append(row.key)
            return category_names

async def _read_category_value(category_key):
    async with aiopg.sa.create_engine(_connection_string) as engine:
        async with engine.acquire() as conn:
            async for row in conn.execute(
                    _configuration_tbl.select().where(_configuration_tbl.c.key == category_key)):
                return row.value

async def _read_category_item(category_key, category_item):
    query_template = """
        SELECT 
            configuration.value::json->'{}' as value
        FROM 
            foglamp.configuration
        WHERE 
            configuration.key='{}'
    """
    query_full = query_template.format(category_item, category_key)
    async with aiopg.sa.create_engine(_connection_string) as engine:
        async with engine.acquire() as conn:
            async for row in conn.execute(text(query_full).columns(_configuration_tbl.c.value)):
                return row.value

async def _read_category_item_value(category_key, category_item):
    query_template = """
        SELECT 
            configuration.value::json->'{}'->'Value' as value
        FROM 
            foglamp.configuration
        WHERE 
            configuration.key='{}'
    """
    query_full = query_template.format(category_item, category_key)
    async with aiopg.sa.create_engine(_connection_string) as engine:
        async with engine.acquire() as conn:
            async for row in conn.execute(text(query_full).columns(_configuration_tbl.c.value)):
                return row.value

async def _update_item_value(category_key, category_item, item_value_replacement):
    query_template = """
            UPDATE foglamp.configuration 
            SET value = jsonb_set(value, '{{{},Value}}', '"{}"') 
            WHERE key='{}'
        """
    query_full = query_template.format(category_item, item_value_replacement, category_key)
    async with aiopg.sa.create_engine(_connection_string) as engine:
        async with engine.acquire() as conn:
            await conn.execute(query_full)

async def get_all_category_names():
    """Get all category names in the FogLAMP system

    Keyword Arguments:
    None

    Return Values:
    a list of strings, each representing a unique category name
    None

    Side Effects:
    None

    Exceptions Raised:
    Unknown

    Restrictions and Usage:
    A FogLAMP component calls this method to obtain all category names in the FogLamp system
    """
    try:
        return await _read_all_category_keys()
    except:
        logging.getLogger(_logger_name).exception(
            'Unable to read all category names')
        raise


async def get_all_category_items(category_name):
    """Get a specified category's entire configuration.

    Keyword Arguments:
    category_name -- name of the category (required)

    Return Values:
    a JSONB dictionary with all items of a category's configuration
    None

    Side Effects:
    None

    Exceptions Raised:
    Unknown

    Restrictions and Usage:
    A FogLAMP component calls this method to obtain a category's configuration
    """
    try:
        return await _read_category_value(category_name)
    except:
        logging.getLogger(_logger_name).exception(
            'Unable to get all category names based on category_name {}'.format(category_name))
        raise


async def get_category_item(category_name, item_name):
    """Get the whole item value for a given item within a given category.

    Keyword Arguments:
    category_name -- name of the category (required)
    item_name -- description of the category (required)

    Return Values:
    a JSONB dictionary with item's whole value
    None

    Side Effects:
    None

    Exceptions Raised:
    Unknown

    Restrictions and Usage:
    A FogLAMP component calls this method to obtain an item's whole value within a specified category
    """
    try:
        return await _read_category_item(category_name, item_name)
    except:
        logging.getLogger(_logger_name).exception(
            'Unable to get category item based on category_name {} and item_name {}'.format(category_name, item_name))
        raise


async def get_item_value(category_name, item_name):
    """Get the Value value for a given item within a given category.

    Keyword Arguments:
    category_name -- name of the category (required)
    item_name -- description of the category (required)

    Return Values:
    a string with the Value value
    None

    Side Effects:
    None

    Exceptions Raised:
    Unknown

    Restrictions and Usage:
    A FogLAMP component calls this method to obtain a Value value.
    """
    try:
        return await _read_category_item_value(category_name, item_name)
    except:
        logging.getLogger(_logger_name).exception(
            'Unable to get category item value entry based on category_name {} and item_name {}'.format(category_name,
                                                                                                        item_name))
        raise


async def set_item_value(category_name, item_name, value_item_entry):
    """Set a category's item's Value entry to a new value.

    Keyword Arguments:
    category_name -- name of the category (required)
    item_name -- name of item within the category whose Value entry needs to be changed (required)
    value_item_entry -- new value to replace old value

    Return Values:
    None

    Side Effects:
    The JSON object storing the configuration for category indexed by category_name will be updated. In particular, the JSON object's item entry referenced by item_name will have it's Value value set to value_item_entry.

    Exceptions Raised:
    Unknown

    Restrictions and Usage:
    A FogLAMP component (admin API included) may call this method to update a cateogry's configuration.
    """
    try:
        return await _update_item_value(category_name, item_name, value_item_entry)
    except:
        logging.getLogger(_logger_name).exception(
            'Unable to set item value entry based on category_name {} and item_name {} and value_item_entry {}'.format(
                category_name, item_name, value_item_entry))
        raise


async def create_category(category_name, category_description, category_json_schema):
    """Create a new category in the database.

    Keyword Arguments:
    category_name -- name of the category (required)
    category_description -- description of the category (required)
    category_json_schema -- JSONB object in dictionary form representing category's configuration values

    Return Values:
    None

    Side Effects:
    Database foglamp.configuration table will have new row with values specified

    Exceptions Raised:
    Duplicate Key
    Null Category Description

    Restrictions and Usage:
    A FogLAMP component calls this method to create one or more new configuration categories to store initial configuration
    """
    try:
        return await _create_new_category(category_name, category_description, category_json_schema)
    except:
        logging.getLogger(_logger_name).exception(
            'Unable to create new category based on category_name {} and category_description {} and category_json_schema {}'.format(
                category_name, category_description, category_json_schema))
        raise
    return None


def register_category(category_name, callback):
    pass

# async def main_test():
#     sample_json = {
#         "port": {
#             "description": "Port to listen on",
#             "default": "5432",
#             "value": "5432",
#             "type": "integer"
#         },
#         "url": {
#             "description": "URL to accept data on",
#             "default": "sensor/reading-values",
#             "Value": "sensor/reading-values",
#             "type": "string"
#         },
#         "certificate": {
#             "description": "X509 certificate used to identify ingress interface",
#             "value": "47676565",
#             "type": "x509 certificate"
#         }
#     }
#
#     print("test create_category")
#     await create_category('CATEG', 'CATEG_DESCRIPTION', sample_json)
#
#     print("test get_all_category_names")
#     rows = await get_all_category_names()
#     for row in rows:
#         print(row)
#
#     print("test get_all_category_items")
#     json = await get_all_category_items('CATEG')
#     print(json)
#     print(type(json))
#
#     print("test get_category_item")
#     json = await get_category_item('CATEG', "url")
#     print(json)
#     print(type(json))
#
#     print("test get_item_value")
#     json = await get_item_value('CATEG', "url")
#     print(json)
#     print(type(json))
#
#     print("test set_item_value")
#     json = await set_item_value('CATEG', "url", "blablabla")
#
#     print("test get_item_value")
#     json = await get_item_value('CATEG', "url")
#     print(json)
#     print(type(json))
#
# if __name__ == '__main__':
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(main_test())