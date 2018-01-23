"""
The following tests the configuration manager component For the most part,
the code uses the boolean type for testing due to simplicity; but contains
tests to verify which data_types are supported and which are not.
"""

import asyncio
import pytest
import sqlalchemy as sa
import aiopg.sa
from sqlalchemy.dialects.postgresql import JSONB
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.storage_client.storage_client import StorageClient

__author__ = "Ori Shadmon"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

pytestmark = pytest.mark.asyncio

_CONNECTION_STRING = "dbname='foglamp'"
_KEYS = ('boolean', 'integer', 'string', 'IPv4', 'IPv6', 'X509 cer', 'password', 'JSON')
_configuration_tbl = sa.Table(
    'configuration',
    sa.MetaData(),
    sa.Column('key', sa.types.CHAR(10)),
    sa.Column('description', sa.types.VARCHAR(255)),
    sa.Column('value', JSONB),
    sa.Column('ts', sa.types.TIMESTAMP)
)

_ADDRESS = pytest.test_env.address
_MGT_PORT = pytest.test_env.core_mgmt_port

_storage = StorageClient(core_management_host=_ADDRESS, core_management_port=_MGT_PORT, svc=None)
cf_mgr = None


async def delete_from_configuration():
    """ Remove initial data from configuration table """
    sql = sa.text("DELETE FROM foglamp.configuration WHERE key IN {}".format(_KEYS))
    async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
        async with engine.acquire() as conn:
            await conn.execute(sql)


@pytest.allure.feature("integration")
@pytest.allure.story("configuration manager")
class TestConfigurationManager:
    """ configuration_manager tests

    The following tests need to be fixed/implemented:
        - FOGL-572: Verification of data type value in configuration manager (new test needs to be added)
    """

    def setup_method(self):
        """ reset configuration table data for specific category_name/s,
        and clear data (if exists) in _registered_interests object"""

        asyncio.get_event_loop().run_until_complete(delete_from_configuration())
        self.cf_mgr = ConfigurationManager(_storage)
        self.cf_mgr._registered_interests.clear()

    def teardown_method(self):
        """reset foglamp data in database, and clear data (if exists)
        in _registered_interests object"""
        asyncio.get_event_loop().run_until_complete(delete_from_configuration())
        self.cf_mgr._registered_interests.clear()

    async def test_accepted_data_types(self):
        """ Test that the accepted data types get inserted

            - create_category
            - get_all_category_names (category_name and category_description)
            - get_category_all_items (category_value by category_name)

        :assert:
            1. Assert that the number of values returned by get_all_category_names
                equals len(data)
            2. category_description returned with get_all_category_names correlates to the
                correct ke
            3. get_category_all_items returns valid category_values for a given key
        """

        data = {
            'boolean': {'category_description': 'boolean type',
                        'category_value': {
                            'info': {
                                'description': 'boolean type with default False',
                                'type': 'boolean',
                                'default': 'False'}}},
            'integer': {'category_description': 'integer type',
                        'category_value': {
                            'info': {
                                'description': 'integer type with default 1',
                                'type': 'integer',
                                'default': '1'}}},
            'string': {'category_description': 'string type',
                       'category_value': {
                           'info': {
                               'description': "string type with default ABCabc",
                               'type': 'string',
                               'default': 'ABCabc'}}},
            'JSON': {'category_description': 'JSON type',
                     'category_value': {
                         'info': {
                             'description': "JSON type with default {}",
                             'type': 'JSON',
                             'default': '{}'}}},
            'IPv4': {'category_description': 'IPv4 type',
                     'category_value': {
                         'info': {
                             'description': "IPv4 type with default 127.0.0.1",
                             'type': 'IPv4',
                             'default': '127.0.0.1'}}},
            'IPv6': {'category_description': 'IPv6 type',
                     'category_value': {
                         'info': {
                             'description': "IPv6 type with default 2001:db8::",
                             'type': 'IPv6',
                             'default': '2001:db8::'}}},
            'X509 cer': {'category_description': 'X509 Certification',
                         'category_value': {
                             'info': {
                                  'description': "X509 Certification",
                                  'type': 'X509 certificate',
                                  'default': 'x509_certificate.cer'}}},
            'password': {'category_description': 'Password Type',
                         'category_value': {
                             'info': {
                                 'description': "Password Type with default",
                                 'type': 'password',
                                 'default': ''}}}
        }

        existing_records = 0

        select_count_stmt = sa.select([sa.func.count()]).select_from(_configuration_tbl)
        async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                result = conn.execute(select_count_stmt)
                async for r in result:
                    existing_records = int(r[0])

        for category_name in data:
            await self.cf_mgr.create_category(category_name=category_name,
                                              category_description=data[category_name]['category_description'],
                                              category_value=data[category_name]['category_value'],
                                              keep_original_items=True)

        sql = sa.text("SELECT * FROM foglamp.configuration WHERE key IN {}".format(_KEYS))
        async with aiopg.sa.create_engine(_CONNECTION_STRING) as engine:
            async with engine.acquire() as conn:
                result = await conn.execute(sql)
                assert 8 == result.rowcount

        categories = await self.cf_mgr.get_all_category_names()
        assert len(categories) == existing_records + 8

        # only filter and test above 8 records

        for key in data:
            # print(key)
            assert key in [cat[0].strip() for cat in categories]
            assert data[key]['category_description'] in [cat[1] for cat in categories]

            category_info = await self.cf_mgr.get_category_all_items(category_name=key)
            assert data[key]['category_value']['info']['description'] == (
                category_info['info']['description'])
            assert data[key]['category_value']['info']['type'] == (
                category_info['info']['type'])
            assert data[key]['category_value']['info']['default'] == (
                category_info['info']['default'])

    async def test_create_category_keep_original_items_true(self):
        """ Test the behavior of create_category when keep_original_items == True

        :assert:
            1. `values` dictionary has both categories
            2. values in 'data' category are as expected
            3. values in 'info' category did not change
        """
        cat_val1 = {'info': {'description': 'boolean type with default False', 'type': 'boolean', 'default': 'False'}}
        await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                          category_value=cat_val1, keep_original_items=False)

        cat_val2 = {'data': {'description': 'int type with default 0', 'type': 'integer', 'default': '0'}}
        await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                          category_value=cat_val2, keep_original_items=True)

        category_info = await self.cf_mgr.get_category_all_items(category_name='boolean')
        # Both category_values exist
        assert sorted(list(category_info.keys())) == ['data', 'info']
        # Verify 'info' category_value
        assert category_info['info']['description'] == 'boolean type with default False'
        assert category_info['info']['type'] == 'boolean'
        assert category_info['info']['default'] == 'False'
        # Verify 'data' category_value
        assert category_info['data']['description'] == 'int type with default 0'
        assert category_info['data']['type'] == 'integer'
        assert category_info['data']['default'] == '0'

    async def test_create_category_keep_original_items_false(self):
        """ Test the behavior of create_category when keep_original_items == False

        :assert:
            1. initial `info` data has been added
            2. `values` dictionary only has 'data' category
            3. values in 'data' category are as expected
        """
        cat_val1 = {'info': {'description': 'boolean type with default False', 'type': 'boolean', 'default': 'False'}}
        await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                          category_value=cat_val1)

        cat_val2 = {'data': {'description': 'int type with default 0', 'type': 'integer', 'default': '0'}}
        await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                          category_value=cat_val2, keep_original_items=False)

        category_info = await self.cf_mgr.get_category_all_items(category_name='boolean')
        # only 'data category_values exist
        assert sorted(list(category_info.keys())) == ['data']
        # Verify 'data' category_value
        assert category_info['data']['description'] == 'int type with default 0'
        assert category_info['data']['type'] == 'integer'
        assert category_info['data']['default'] == '0'

    async def test_create_category_with_quoted_json_data(self):
        """ Test the behavior of create_category when quoted string in json data
        """
        cat_val = {"data": {'description': "string type with 'default' value", 'type': 'string', 'default': 'test'}}
        await self.cf_mgr.create_category(category_name='string', category_description='boolean type',
                                          category_value=cat_val, keep_original_items=False)

        category_info = await self.cf_mgr.get_category_all_items(category_name='string')
        assert category_info['data']['description'] == "string type with 'default' value"
        assert category_info['data']['type'] == 'string'
        assert category_info['data']['default'] == 'test'

    async def test_set_category_item_value_entry(self):
        """ Test updating of configuration.value for a specific key using

            - create_category to create the category
            - get_category_item_value_entry to check category_value
            - set_category_item_value_entry to update category_value

        :assert:
            1. `default` and `value` in configuration.value are the same
            2. `value` in configuration.value gets updated, while `default` does not
        """
        cat_val = {'info': {'description': 'boolean type with default False', 'type': 'boolean', 'default': 'False'}}
        await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                          category_value=cat_val)
        result = await self.cf_mgr.get_category_item_value_entry(category_name='boolean', item_name='info')
        assert result == 'False'

        await self.cf_mgr.set_category_item_value_entry(category_name='boolean', item_name='info',
                                                        new_value_entry='True')
        result = await self.cf_mgr.get_category_item_value_entry(category_name='boolean', item_name='info')
        assert result == 'True'

    async def test_get_category_item(self):
        """ Test that get_category_item returns all the data in configuration.

        :assert:
            Information in configuration.value match the category_values declared

        """
        cat_val = {'info': {'description': 'boolean type with default False', 'type': 'boolean', 'default': 'False'}}
        await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                          category_value=cat_val)
        result = await self.cf_mgr.get_category_item(category_name='boolean', item_name='info')
        assert result['description'] == 'boolean type with default False'
        assert result['type'] == 'boolean'
        assert result['default'] == 'False'
        assert result['value'] == 'False'

    async def test_create_category_invalid_dict(self):
        """ Test that create_category returns the expected error when category_value is a 'string' rather than a JSON

        :assert:
            Assert that TypeError gets returned when type is not dict
        """
        with pytest.raises(TypeError) as error_exec:
            await self.cf_mgr.create_category(category_name='integer', category_description='integer type',
                                              category_value='1')
        assert "TypeError: category_val must be a dictionary" in str(error_exec)

    async def test_create_category_invalid_name(self):
        """ Test that create_category returns the expected error when name is invalid

        :assert:
            Assert that TypeError gets returned when name is not allowed other than string
        """
        cat_val = {'info': {'description': 'invalid name with None type', 'type': 'None', 'default': 'none'}}
        with pytest.raises(TypeError) as error_exec:
            await self.cf_mgr.create_category(category_name=None, category_description='invalid name',
                                              category_value=cat_val)
        assert "TypeError: category_name must be a string" in str(error_exec)

    async def test_create_category_invalid_type(self):
        """ Test that create_category returns the expected error when type is invalid

        :assert:
            Assert that TypeError gets returned when type is not allowed e.g. float
        """
        cat_val = {'info': {'description': 'float type with default 1.1', 'type': 'float', 'default': '1.1'}}
        with pytest.raises(ValueError) as error_exec:
            await self.cf_mgr.create_category(category_name='float', category_description='float type',
                                              category_value=cat_val)
        assert ('ValueError: Invalid entry_val for entry_name "type" for item_name info. valid: ' +
                "['boolean', 'integer', 'string', 'IPv4', " +
                "'IPv6', 'X509 certificate', 'password', 'JSON']") in str(error_exec)

    async def test_create_category_case_sensitive_type(self):
        """ Test that create_category returns the expected error when type is upper case

        :assert:
            Assert that TypeError gets returned when type is uppercase e.g. INTEGER
        """
        # TODO: should be case insensitive? EVEN for this SCREAMING_SNAKE_CASE makes more sense!
        # e.g. X509_CERTIFICATE, IPV4 etc.
        cat_val = {'info': {'description': 'INTEGER type with default 1', 'type': 'INTEGER', 'default': '1'}}
        with pytest.raises(ValueError) as error_exec:
            await self.cf_mgr.create_category(category_name='INTEGER', category_description='INTEGER type',
                                              category_value=cat_val)
        assert ('ValueError: Invalid entry_val for entry_name "type" for item_name info. valid: ' +
                "['boolean', 'integer', 'string', 'IPv4', " +
                "'IPv6', 'X509 certificate', 'password', 'JSON']") in str(error_exec)

    async def test_create_category_invalid_entry_value_for_type(self):
        """ Test the case where value is set to the actual "value" rather than the string of the value

        :assert:
            Assert TypeError when type is set to bool rather than 'boolean'
        """
        cat_val = {'info': {'description': 'boolean type with default False', 'type': bool, 'default': 'False'}}
        with pytest.raises(TypeError) as error_exec:
            await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                              category_value=cat_val)
        assert ("TypeError: entry_val must be a string for item_name " +
                "info and entry_name type") in str(error_exec)

    async def test_create_category_invalid_entry_value_for_default(self):
        """ Test the case where value is set to the actual value as per type instead of string of the value

        :assert:
            Assert TypeError when default is set to False rather than 'False'
        """

        cat_val = {'info': {'description': 'boolean type with default False', 'type': 'boolean', 'default': False}}
        with pytest.raises(TypeError) as error_exec:
            await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                              category_value=cat_val)
        assert ("TypeError: entry_val must be a string for item_name "
                "info and entry_name default") in str(error_exec)

    async def test_create_category_invalid_entry_none_for_description(self):
        """Test the case where value is set to None instead of string of the value

        :assert:
            Assert TypeError when description is set to None rather than  string
            note: Empty string is allowed for description
        """
        cat_val = {'info': {'description': None, 'type': 'boolean', 'default': 'False'}}
        with pytest.raises(TypeError) as error_exec:
            await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                              category_value=cat_val)
        assert ("TypeError: entry_val must be a string for item_name " +
                "info and entry_name description") in str(error_exec)

    async def test_create_category_missing_entry_for_type(self):
        """ Test that create_category returns the expected error when category_value entry_name type is missing

        :assert:
            Assert ValueError when type is missing
        """
        cat_val = {'info': {'description': 'boolean type with default False', 'default': 'False'}}

        with pytest.raises(ValueError) as error_exec:
            await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                              category_value=cat_val)
        assert "ValueError: Missing entry_name type for item_name info" in str(error_exec)

    async def test_create_category_missing_entry_for_description(self):
        """ Test that create_category returns the expected error when category_value entry_name description is missing

        :assert:
            Assert ValueError when description is missing
        """
        cat_val = {'info': {'type': 'boolean', 'default': 'False'}}
        with pytest.raises(ValueError) as error_exec:
            await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                              category_value=cat_val)
        assert "ValueError: Missing entry_name description for item_name info" in str(error_exec)

    async def test_create_category_missing_value_for_default(self):
        """
        Test that create_category returns the expected error when category_value entry_name default value is missing

        :assert:
            Assert ValueError when default is missing
        """
        cat_val = {'info': {'description': 'integer type with value False', 'type': 'integer'}}

        with pytest.raises(ValueError) as error_exec:
            await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                              category_value=cat_val)
        assert "ValueError: Missing entry_name default for item_name info" in str(error_exec)

    async def test_create_category_invalid_description(self):
        """ Test that create_category returns the expected error when description is invalid

        :assert:
            Assert that TypeError gets returned when description is not allowed other than string
        """
        cat_val = {'info': {'description': 'boolean type with default False', 'type': 'boolean', 'default': 'False'}}
        with pytest.raises(TypeError) as error_exec:
            await self.cf_mgr.create_category(category_name="boolean", category_description=None,
                                              category_value=cat_val)
        assert "TypeError: category_description must be a string" in str(error_exec)

    async def test_set_category_item_value_error(self):
        """ Test update of configuration.value when category_name or item_name does not exist

        :assert:
             Assert that ValueError gets returned on either category_name nor item_name does not exist
        """
        with pytest.raises(ValueError) as error_exec:
            await self.cf_mgr.set_category_item_value_entry(category_name='boolean', item_name='info',
                                                            new_value_entry='True')

        assert "ValueError: No detail found for the category_name: boolean and item_name: info"\
               in str(error_exec)

    async def test_get_category_item_value_entry_dne(self):
        """ Test that None gets returned when either category_name and/or item_name don't exist

        :assert:
            1. Assert None is returned when item_name does not exist
            2. Assert None is returned when category_name does not exist
        """
        cat_val = {'info': {'description': 'boolean type with default False', 'type': 'boolean', 'default': 'False'}}
        await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                          category_value=cat_val)
        result = await self.cf_mgr.get_category_item_value_entry(category_name='boolean', item_name='data')
        assert result is None

        result = await self.cf_mgr.get_category_item_value_entry(category_name='integer', item_name='info')
        assert result is None

    async def test_get_category_item_empty(self):
        """ Test that get_category_item when either category_name or item_name do not exist

        :assert:
            Assert result is None when category_name or item_name do not exist in configuration
        """
        cat_val = {'info': {'description': 'boolean type with default False', 'type': 'boolean', 'default': 'False'}}
        await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                          category_value=cat_val)
        result = await self.cf_mgr.get_category_item(category_name='integer', item_name='info')
        assert result is None

        result = await self.cf_mgr.get_category_item(category_name='boolean', item_name='data')
        assert result is None

    async def test_get_category_all_items_done(self):
        """ Test get_category_all_items doesn't return anything if category_name doesn't exist

        :assert:
            Assert None gets returned when category_name does not exist
        """
        cat_val = {'info': {'description': 'boolean type with default False', 'type': 'boolean', 'default': 'False'}}
        await self.cf_mgr.create_category(category_name='boolean', category_description='boolean type',
                                          category_value=cat_val)

        result = await self.cf_mgr.get_category_all_items(category_name='integer')
        assert result is None

    async def test_register_interest(self):
        """ Test that when register_interest is called, _registered_interests gets updated

        :assert:
           for (category_name='boolean', callback='tests.callback')
           the value for _register_interests['boolean'] is {'tests.callback'}
        """
        self.cf_mgr.register_interest(category_name='boolean', callback='tests.callback')
        assert list(self.cf_mgr._registered_interests.keys())[0] == 'boolean'
        assert self.cf_mgr._registered_interests['boolean'] == {'tests.callback'}

    async def test_register_interest_category_name_none_error(self):
        """ Test that error gets returned when category_name is None

        :assert:
            Assert error message when category_name is None
        """
        with pytest.raises(ValueError) as error_exec:
            self.cf_mgr.register_interest(category_name=None, callback='foglamp.callback')
        assert "ValueError: Failed to register interest. category_name cannot be None" in (
            str(error_exec))

    async def test_register_interest_callback_none_error(self):
        """ Test that error gets returned when callback is None

           :assert:
               Assert error message when callback is None
        """
        with pytest.raises(ValueError) as error_exec:
            self.cf_mgr.register_interest(category_name='integer', callback=None)
        assert "ValueError: Failed to register interest. callback cannot be None" in (
            str(error_exec))

    async def test_unregister_interest_0_callback(self):
        """ Test that when unregister_interest is called and name/callback combo does not 
            exist, nothing happens

        :assert:
           for (category_name='boolean', callback='tests.callback')
           the value for _register_interests['boolean'] is {'tests.callback'}
        """
        self.cf_mgr.unregister_interest(category_name='boolean', callback='tests.callback')
        assert len(self.cf_mgr._registered_interests) == 0
       
    async def test_unregister_interest_1_callback(self):
        """ Test that when unregister_interest is called and only one callback exists for 
            the name, _registered_interests removes the dictionary item for that name

        :assert:
           for (category_name='boolean', callback='tests.callback')
           the value for _register_interests['boolean'] is {'tests.callback'}
        """
        self.cf_mgr.register_interest(category_name='boolean', callback='tests.callback')
        self.cf_mgr.unregister_interest(category_name='boolean', callback='tests.callback')
        assert len(self.cf_mgr._registered_interests) == 0

    async def test_unregister_interest_2_callback(self):
        """ Test that when unregister_interest is called and only one callback exists for 
            the name, _registered_interests removes only the single callback from the list

        :assert:
           for (category_name='boolean', callback='tests.callback')
           the value for _register_interests['boolean'] is {'tests.callback'}
        """
        self.cf_mgr.register_interest(category_name='boolean', callback='tests.callback')
        self.cf_mgr.register_interest(category_name='boolean', callback='tests.callback2')
        self.cf_mgr.unregister_interest(category_name='boolean', callback='tests.callback')
        assert list(self.cf_mgr._registered_interests.keys())[0] == 'boolean'
        assert self.cf_mgr._registered_interests['boolean'] == {'tests.callback2'}

    async def test_unregister_interest_category_name_none_error(self):
        """ Test that error gets returned when category_name is None

        :assert:
            Assert error message when category_name is None
        """
        with pytest.raises(ValueError) as error_exec:
            self.cf_mgr.unregister_interest(category_name=None, callback='foglamp.callback')
        assert "ValueError: Failed to unregister interest. category_name cannot be None" in (
            str(error_exec))

    async def test_unregister_interest_callback_none_error(self):
        """ Test that error gets returned when callback is None

           :assert:
               Assert error message when callback is None
        """
        with pytest.raises(ValueError) as error_exec:
            self.cf_mgr.unregister_interest(category_name='integer', callback=None)
        assert "ValueError: Failed to unregister interest. callback cannot be None" in (
            str(error_exec))
