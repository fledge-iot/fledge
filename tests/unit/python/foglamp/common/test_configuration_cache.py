# -*- coding: utf-8 -*-

import pytest
from foglamp.common.configuration_manager import ConfigurationCache

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "configuration_manager", "configuration_cache")
class TestConfigurationCache:

    def test_init(self):
        cached_manager = ConfigurationCache()
        assert {} == cached_manager.cache
        assert 10 == cached_manager.max_cache_size
        assert 0 == cached_manager.hit
        assert 0 == cached_manager.miss

    def test_size(self):
        cached_manager = ConfigurationCache()
        assert 0 == cached_manager.size

    def test_contains_with_no_cache(self):
        cached_manager = ConfigurationCache()
        assert cached_manager.__contains__("Blah") is False

    def test_contains_with_cache(self):
        cached_manager = ConfigurationCache()
        cached_manager.cache = {"test_cat": {'value': {'config_item': {'default': 'woo', 'description': 'foo', 'type': 'string'}}}}
        assert cached_manager.__contains__("test_cat") is True

    def test_update(self):
        cached_manager = ConfigurationCache()
        cat_name = "test_cat"
        cat_val = {'config_item': {'default': 'woo', 'description': 'foo', 'type': 'string'}}
        cached_manager.cache = {cat_name: {'value': {}}}
        cached_manager.update(cat_name, cat_val)
        assert 'date_accessed' in cached_manager.cache[cat_name]
        assert cat_val == cached_manager.cache[cat_name]['value']

    def test_remove_oldest(self):
        cached_manager = ConfigurationCache()
        cached_manager.update("cat1", {'value': {}})
        cached_manager.update("cat2", {'value': {}})
        cached_manager.update("cat3", {'value': {}})
        cached_manager.update("cat4", {'value': {}})
        cached_manager.update("cat5", {'value': {}})
        cached_manager.update("cat6", {'value': {}})
        cached_manager.update("cat7", {'value': {}})
        cached_manager.update("cat8", {'value': {}})
        cached_manager.update("cat9", {'value': {}})
        cached_manager.update("cat10", {'value': {}})
        assert 10 == cached_manager.size
        cached_manager.update("cat11", {'value': {}})
        assert 'cat1' not in cached_manager.cache
        assert 'cat2' in cached_manager.cache
        assert 'cat3' in cached_manager.cache
        assert 'cat4' in cached_manager.cache
        assert 'cat5' in cached_manager.cache
        assert 'cat6' in cached_manager.cache
        assert 'cat7' in cached_manager.cache
        assert 'cat8' in cached_manager.cache
        assert 'cat9' in cached_manager.cache
        assert 'cat10' in cached_manager.cache
        assert 'cat11' in cached_manager.cache
        assert 10 == cached_manager.size

    def test_remove(self):
        cached_manager = ConfigurationCache()
        cached_manager.update("cat1", {'value': {}})
        cached_manager.update("cat2", {'value': {}})
        cached_manager.update("cat3", {'value': {}})
        cached_manager.update("cat4", {'value': {}})
        assert 4 == cached_manager.size
        cached_manager.remove("cat2")
        assert 3 == cached_manager.size
        assert 'cat2' not in cached_manager.cache
        assert 'cat1' in cached_manager.cache
        assert 'cat3' in cached_manager.cache
        assert 'cat4' in cached_manager.cache
