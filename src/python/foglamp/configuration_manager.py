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

""" 
DB - postgres
    tablespace: foglamp
    table: configuration
    columns:
        foglamp.configuration.key - char(5)
        foglamp.configuration.value - jsonb
        foglamp.configuration.ts - timestamp(6) with timezone
DB Operations:
    create single row
    read single row
    update single row
    delete single row
    read all rows
        
"""

_configuration_tbl = sa.Table(
    'configuration',
    sa.MetaData(),
    sa.Column('key', sa.types.CHAR(5)),
    sa.Column('value', JSONB),
    sa.Column('ts', sa.types.TIMESTAMP)
)
"""Defines the table that data will be inserted into"""

async def _create_new_category(category_name, category_json_schema):
    # TODO: too long category_name
    # TODO: proper duplicate key handling
    try:
        async with aiopg.sa.create_engine('postgresql://foglamp:foglamp@localhost:5432/foglamp') as engine:
            async with engine.acquire() as conn:
                try:
                    await conn.execute(_configuration_tbl.insert().values(key=category_name, value=category_json_schema))
                except psycopg2.IntegrityError:
                    logging.getLogger('configuration-manager').exception('Duplicate key (%s) inserting configuration:\n%s', category_name, category_json_schema)
    except Exception:
        logging.getLogger('configuration-manager').exception('category_name (%s) category_json_schema:\n%s', category_name, category_json_schema)
        print("error")

async def _read_all_category_keys():
    try:
        async with aiopg.sa.create_engine('postgresql://foglamp:foglamp@localhost:5432/foglamp') as engine:
            async with engine.acquire() as conn:
                category_names = []
                async for row in conn.execute(_configuration_tbl.select()):
                    category_names.append(row.key)
                return category_names
    except Exception:
        logging.getLogger('configuration-manager').exception('Unable to read all category names')
        print("error")

async def _read_category_value(category_key):
    try:
        async with aiopg.sa.create_engine('postgresql://foglamp:foglamp@localhost:5432/foglamp') as engine:
            async with engine.acquire() as conn:
                async for row in conn.execute(_configuration_tbl.select().where(_configuration_tbl.c.key==category_key)):
                    return row.value
    except Exception:
        logging.getLogger('configuration-manager').exception('Unable to read all category names')
        print("error")
    return None

async def _read_category_item(category_key, category_item):
    query_template="""
        SELECT 
            configuration.value::json->'{}' as value
        FROM 
            foglamp.configuration
        WHERE 
            configuration.key='{}'
    """
    query_full = query_template.format(category_item, category_key)
    try:
        async with aiopg.sa.create_engine('postgresql://foglamp:foglamp@localhost:5432/foglamp') as engine:
            async with engine.acquire() as conn:
                async for row in conn.execute(text(query_full).columns(_configuration_tbl.c.value)):
                    return row.value
    except Exception:
        logging.getLogger('configuration-manager').exception('Unable to read all category items')
        print("error")
    return None

async def _read_category_item_value(category_key, category_item):
    query_template="""
        SELECT 
            configuration.value::json->'{}'->'Value' as value
        FROM 
            foglamp.configuration
        WHERE 
            configuration.key='{}'
    """
    query_full = query_template.format(category_item, category_key)
    try:
        async with aiopg.sa.create_engine('postgresql://foglamp:foglamp@localhost:5432/foglamp') as engine:
            async with engine.acquire() as conn:
                async for row in conn.execute(text(query_full).columns(_configuration_tbl.c.value)):
                    return row.value
    except Exception:
        logging.getLogger('configuration-manager').exception('Unable to read all category items')
        print("error")
    return None


"""UPDATE foglamp.configuration SET value = jsonb_set(value, '{url,Value}', '"new"') WHERE key='CAT';
"""
async def _update_item_value(category_key, category_item, item_value_replacement):
    query_template = """
            UPDATE foglamp.configuration 
            SET value = jsonb_set(value, '{{{},Value}}', '"{}"') 
            WHERE key='{}'
        """
    query_full = query_template.format(category_item, item_value_replacement, category_key)
    # print(query_full)

    try:
        async with aiopg.sa.create_engine('postgresql://foglamp:foglamp@localhost:5432/foglamp') as engine:
            async with engine.acquire() as conn:
                await conn.execute(query_full)
    except Exception:
        logging.getLogger('configuration-manager').exception('Unable to update category_name (%s) category_item (%s) with new Value (%s)', category_key, category_item, item_value_replacement)
        print("error")

"""
Returns all keys held in the DB
Param: none
Behavior:
    Call storage api
    request all category names
Results:
    Non-empty
    empty
"""
def get_all_category_names():
    # TODO: return string?
    # TODO: throw exception if empty?
    return asyncio.get_event_loop().run_until_complete(_read_all_category_keys())

"""
Return JSON object associated with specified key
Param: category_name
Behavior
    Call storage api
    Request JSON object given category_name
Result
    Category exists
        Empty json
        Nonempty json
    Category does not exist
"""
def get_all_category_items(category_name):
    # query DB for JSON obj for corresponding category_name
    # TODO: throw exception if category_name doesn't exist?
    return asyncio.get_event_loop().run_until_complete(_read_category_value(category_name))

"""
Return item associated with a category and an item name
Param: category_name, item_name
Behavior:
    Call storage api
    Request JSON object given category_name
    Retrieve item from JSON object
Result:
    Category exists
        Empty json
        Nonempty json
            Item_name doesn’t exist
            Item_name_exists
                empty item_entries
                Non-empty item_entries
    Category does not exist
"""
def get_category_item(category_name, item_name):
    return asyncio.get_event_loop().run_until_complete(_read_category_item(category_name, item_name))

"""
Return “Value” item_entry of a given item in a given category
Param: category_name, item_name
Behavior:
    Call storage api
    Request JSON object given category_name
    Retrieve item from JSON object
    Retrieve “value” iterm_entry from item
Result:
    Category exists
        Empty json
        Nonempty json
            Item_name doesn’t exist
            Item_name_exists
                empty item_entries
                Non-empty item_entries
                    “Value” item entry exits
                        Empty
                        Nonempty 
                    “Value” item entry does not exist
    Category does not exist
"""
def get_item_value(category_name, item_name):
    return asyncio.get_event_loop().run_until_complete(_read_category_item_value(category_name, item_name))

"""
TODO: https://stackoverflow.com/questions/26703476/how-to-perform-update-operations-on-columns-of-type-jsonb-in-postgres-9-4
Set the value property in the JSON object
Param: category_name, item_name, value_item_entry
Behavior:
    Call storage api
    Request JSON object given category_name
    Modify “Value” item_entry of item_name specified
    JSON manipulation to be done in storage manager code or within storage service code?
    I would not do it in the storage system, but rather in the config code itself. The storage system would not “understand” the JSON object, merely treat it as a blob.
    Persist change, along with timestamp
    Parse and validate replacement value within the limited confirms of the validation we do
Result:
    Category_name exists
        Item_name exists
            Value Item_entry exists
                Value item_entry is updated
                    Value item_entry does not exist
        Item_name does not exist
    Category_name does not exist
"""
def set_item_value(category_name, item_name, value_item_entry):
    return asyncio.get_event_loop().run_until_complete(_update_item_value(category_name, item_name, value_item_entry))

"""
Create a configuration category within the configuration database (with merge operation)
Param: category_name, category_json_schema
Behavior:
    Call Storage API
    Storage api checks to see if category exists
    Create new category if one doesn’t already exist
Result:
    Category_name exists
    Category_name does not exist
        Category_name created
        JSON object specified as value
        Timestamp updates
-------------------------------------------------------------------------------
    How much validation should we do?
        Very little, we should test each item has a name and type, but that is about the limit of it
    Are we only setting up form, or will Value item_entries also be included?
        Default values may be specified when the config category gets created, in this case the newly created config item will have the value taken from the default.
"""
def create_category(category_name, category_json_schema):
    # TODO: check if category_name already exists
    # TODO: validate JSON object has proper form
    return asyncio.get_event_loop().run_until_complete(_create_new_category(category_name, category_json_schema))

"""
Register interest in a configuration category
Registers a callback that will be called if there are any modifications to the config category given in the call
Param: category_name, callback
-------------------------------------------------------------------------------
Will the interest registration be persisted in the database?
    No, there is no need as the code will do the same thing the next time it is started.
What does a callback look like?
    Honest answer, don’t know, it will be something like categoryChange(categoryName, categoryJSON) - maybe
"""
def register_category(category_name, callback):
    pass

if __name__ == '__main__':
    sample_json={
      "port" : {
          "description" : "Port to listen on",
          "default"       : "5432",
          "value"         : "5432",
          "type"           : "integer"
      },
      "url" :  {
          "description" : "URL to accept data on",
          "default"        : "sensor/reading-values",
          "Value"          : "sensor/reading-values",
          "type"            : "string"
       },
       "certificate" :  {
          "description" : "X509 certificate used to identify ingress interface",
          "value"         : "47676565",
          "type"           : "x509 certificate"
        }
}

    print("test create_category")
    create_category('CATEG',sample_json)

    print("test get_all_category_names")
    rows = get_all_category_names()
    for row in rows:
        print(row)

    print("test get_all_category_items")
    json = get_all_category_items('CATEG')
    print(json)
    print(type(json))

    print("test get_category_item")
    json = get_category_item('CATEG',"url")
    print(json)
    print(type(json))

    print("test get_item_value")
    json = get_item_value('CATEG', "url")
    print(json)
    print(type(json))

    print("test set_item_value")
    json = set_item_value('CATEG', "url","blablabla")

    print("test get_item_value")
    json = get_item_value('CATEG', "url")
    print(json)
    print(type(json))