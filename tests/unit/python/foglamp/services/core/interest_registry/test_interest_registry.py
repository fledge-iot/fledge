# -*- coding: utf-8 -*-

import pytest
from unittest.mock import MagicMock
from unittest.mock import patch
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core.interest_registry.interest_registry import InterestRegistry
from foglamp.services.core.interest_registry.interest_registry import InterestRegistrySingleton
from foglamp.services.core.interest_registry.interest_record import InterestRecord
from foglamp.services.core.interest_registry import exceptions as interest_registry_exceptions

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "interest-registry")
class TestInterestRegistry:
    @pytest.fixture()
    def reset_singleton(self):
        # executed before each test
        InterestRegistrySingleton._shared_state = {}
        yield
        InterestRegistrySingleton._shared_state = {}

    def test_constructor_no_configuration_manager_defined_no_configuration_manager_passed(
            self, reset_singleton):
        # first time initializing InterestRegistry without configuration manager
        # produces error
        with pytest.raises(TypeError) as excinfo:
            InterestRegistry()
        assert 'Must be a valid ConfigurationManager object' in str(
            excinfo.value)

    def test_constructor_no_configuration_manager_defined_configuration_manager_passed(
            self, reset_singleton):
        # first time initializing InterestRegistry with configuration manager
        # works
        configuration_manager_mock = MagicMock(spec=ConfigurationManager)
        i_reg = InterestRegistry(configuration_manager_mock)
        assert hasattr(i_reg, '_configuration_manager')
        assert isinstance(i_reg._configuration_manager, ConfigurationManager)
        assert hasattr(i_reg, '_registered_interests')

    def test_constructor_configuration_manager_defined_configuration_manager_passed(
            self, reset_singleton):
        configuration_manager_mock = MagicMock(spec=ConfigurationManager)
        # second time initializing InterestRegistry with new configuration manager
        # works
        configuration_manager_mock2 = MagicMock(spec=ConfigurationManager)
        i_reg = InterestRegistry(configuration_manager_mock)
        i_reg2 = InterestRegistry(configuration_manager_mock2)
        assert hasattr(i_reg2, '_configuration_manager')
        # ignore new configuration manager
        assert isinstance(i_reg2._configuration_manager, ConfigurationManager)
        assert hasattr(i_reg2, '_registered_interests')

    def test_constructor_configuration_manager_defined_no_configuration_manager_passed(
            self, reset_singleton):
        configuration_manager_mock = MagicMock(spec=ConfigurationManager)
        i_reg = InterestRegistry(configuration_manager_mock)
        # second time initializing InterestRegistry without configuration manager
        i_reg2 = InterestRegistry()
        assert hasattr(i_reg2, '_configuration_manager')
        assert isinstance(i_reg2._configuration_manager, ConfigurationManager)
        assert hasattr(i_reg2, '_registered_interests')
        assert len(i_reg._registered_interests) == 0

    def test_register(self, reset_singleton):
        configuration_manager_mock = MagicMock(spec=ConfigurationManager)
        i_reg = InterestRegistry(configuration_manager_mock)
        # register the first interest
        microservice_uuid = 'muuid'
        category_name = 'catname'
        ret_val = i_reg.register(microservice_uuid, category_name)
        assert ret_val is not None
        assert len(i_reg._registered_interests) is 1
        assert isinstance(i_reg._registered_interests[0], InterestRecord)
        assert i_reg._registered_interests[0]._registration_id is ret_val
        assert i_reg._registered_interests[0]._microservice_uuid is microservice_uuid
        assert i_reg._registered_interests[0]._category_name is category_name
        str_val = 'interest registration id={}: <microservice uuid={}, category_name={}>'.format(
            ret_val, microservice_uuid, category_name)
        assert str(i_reg._registered_interests[0]) == str_val

        # register an existing interest
        with pytest.raises(interest_registry_exceptions.ErrorInterestRegistrationAlreadyExists) as excinfo:
            ret_val = i_reg.register(microservice_uuid, category_name)
        assert ret_val is not None
        assert len(i_reg._registered_interests) is 1
        assert isinstance(i_reg._registered_interests[0], InterestRecord)
        assert i_reg._registered_interests[0]._registration_id is ret_val
        assert i_reg._registered_interests[0]._microservice_uuid is microservice_uuid
        assert i_reg._registered_interests[0]._category_name is category_name
        str_val = 'interest registration id={}: <microservice uuid={}, category_name={}>'.format(
            ret_val, microservice_uuid, category_name)
        assert str(i_reg._registered_interests[0]) == str_val

        # register a second interest
        category_name2 = 'catname2'
        ret_val = i_reg.register(microservice_uuid, category_name2)
        assert ret_val is not None
        assert len(i_reg._registered_interests) is 2
        assert isinstance(i_reg._registered_interests[1], InterestRecord)
        assert i_reg._registered_interests[1]._registration_id is ret_val
        assert i_reg._registered_interests[1]._microservice_uuid is microservice_uuid
        assert i_reg._registered_interests[1]._category_name is category_name2
        str_val = 'interest registration id={}: <microservice uuid={}, category_name={}>'.format(
            ret_val, microservice_uuid, category_name2)
        assert str(i_reg._registered_interests[1]) == str_val

    def test_unregister(self, reset_singleton):
        configuration_manager_mock = MagicMock(spec=ConfigurationManager)
        i_reg = InterestRegistry(configuration_manager_mock)
        # unregister when no items exists
        fake_uuid = 'bla'
        with pytest.raises(interest_registry_exceptions.DoesNotExist) as excinfo:
            ret_val = i_reg.unregister(fake_uuid)

        # register 2 interests, then unregister 1
        id_1_1 = i_reg.register('muuid1', 'catname1')
        id_1_2 = i_reg.register('muuid1', 'catname2')
        ret_val = i_reg.unregister(id_1_1)
        assert ret_val == id_1_1
        assert len(i_reg._registered_interests) is 1
        assert isinstance(i_reg._registered_interests[0], InterestRecord)
        assert i_reg._registered_interests[0]._registration_id is id_1_2
        assert i_reg._registered_interests[0]._microservice_uuid is 'muuid1'
        assert i_reg._registered_interests[0]._category_name is 'catname2'

        # unregister the second one
        ret_val = i_reg.unregister(id_1_2)
        assert ret_val == id_1_2
        assert len(i_reg._registered_interests) is 0

    def test_get(self, reset_singleton):
        configuration_manager_mock = MagicMock(spec=ConfigurationManager)
        i_reg = InterestRegistry(configuration_manager_mock)

        # get when empty
        microservice_uuid = 'muuid'
        category_name = 'catname'
        with pytest.raises(interest_registry_exceptions.DoesNotExist) as excinfo:
            i_reg.get(microservice_uuid=microservice_uuid,
                      category_name=category_name)

        # get when there is a result (use patch on 'get')
        with patch.object(InterestRegistry, 'and_filter', return_value=[1]):
            ret_val = i_reg.get(
                microservice_uuid=microservice_uuid, category_name=category_name)
        assert ret_val is not None
        assert ret_val == [1]

    def test_get_with_and_filter(self, reset_singleton):
        configuration_manager_mock = MagicMock(spec=ConfigurationManager)
        i_reg = InterestRegistry(configuration_manager_mock)
        # register some interts
        id_1_1 = i_reg.register('muuid1', 'catname1')
        id_1_2 = i_reg.register('muuid1', 'catname2')
        id_2_1 = i_reg.register('muuid2', 'catname1')
        id_2_2 = i_reg.register('muuid2', 'catname2')
        id_3_3 = i_reg.register('muuid3', 'catname3')

        ret_val = i_reg.get(microservice_uuid='muuid1')
        assert len(ret_val) is 2
        for i in ret_val:
            assert isinstance(i, InterestRecord)
        assert ret_val[0]._registration_id is id_1_1
        assert ret_val[0]._microservice_uuid is 'muuid1'
        assert ret_val[0]._category_name is 'catname1'
        assert ret_val[1]._registration_id is id_1_2
        assert ret_val[1]._microservice_uuid is 'muuid1'
        assert ret_val[1]._category_name is 'catname2'

        ret_val = i_reg.get(category_name='catname2')
        assert len(ret_val) is 2
        for i in ret_val:
            assert isinstance(i, InterestRecord)
        assert ret_val[0]._registration_id is id_1_2
        assert ret_val[0]._microservice_uuid is 'muuid1'
        assert ret_val[0]._category_name is 'catname2'
        assert ret_val[1]._registration_id is id_2_2
        assert ret_val[1]._microservice_uuid is 'muuid2'
        assert ret_val[1]._category_name is 'catname2'

        ret_val = i_reg.get(category_name='catname2',
                            microservice_uuid='muuid2')
        assert len(ret_val) is 1
        for i in ret_val:
            assert isinstance(i, InterestRecord)
        assert ret_val[0]._registration_id is id_2_2
        assert ret_val[0]._microservice_uuid is 'muuid2'
        assert ret_val[0]._category_name is 'catname2'
