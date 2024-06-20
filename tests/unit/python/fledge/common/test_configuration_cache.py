# -*- coding: utf-8 -*-

import pytest
from fledge.common.configuration_manager import ConfigurationCache

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "configuration_manager", "configuration_cache")
class TestConfigurationCache:

    @pytest.mark.parametrize("size", [
        1, 10, 20, 1000
    ])
    def test_init(self, size):
        cached_manager = ConfigurationCache(size)
        assert {} == cached_manager.cache
        assert size == cached_manager.max_cache_size
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
        cached_manager.cache = {"test_cat": {'value': {'config_item': {'default': 'woo', 'description': 'foo',
                                                                       'type': 'string'}}}}
        assert cached_manager.__contains__("test_cat") is True

    def test_update(self):
        cached_manager = ConfigurationCache()
        cat_name = "test_cat"
        cat_desc = "test_desc"
        cat_val = {'config_item': {'default': 'woo', 'description': 'foo', 'type': 'string'}}
        cat_display_name = "AJ"
        cached_manager.cache = {cat_name: {'value': {}}}
        cached_manager.update(cat_name, cat_desc, cat_val)
        assert 'date_accessed' in cached_manager.cache[cat_name]
        assert cat_desc == cached_manager.cache[cat_name]['description']
        assert cat_val == cached_manager.cache[cat_name]['value']
        assert cat_name == cached_manager.cache[cat_name]['displayName']

        cached_manager.update(cat_name, cat_desc, cat_val, cat_display_name)
        assert 'date_accessed' in cached_manager.cache[cat_name]
        assert cat_desc == cached_manager.cache[cat_name]['description']
        assert cat_val == cached_manager.cache[cat_name]['value']
        assert cat_display_name == cached_manager.cache[cat_name]['displayName']

    @pytest.mark.parametrize("size, cat_names, cat_miss", [
        (1, ['cat10'], ['cat1', 'cat2', 'cat3', 'cat4', 'cat5', 'cat6', 'cat7', 'cat8', 'cat9']),
        (2, ['cat9', 'cat10'], ['cat1', 'cat2', 'cat3', 'cat4', 'cat5', 'cat6', 'cat7', 'cat8']),
        (10, ['cat1', 'cat2', 'cat3', 'cat4', 'cat5', 'cat6', 'cat7', 'cat8', 'cat9', 'cat10'], [])
    ])
    def test_update_with_cache_size(self, size, cat_names, cat_miss):
        cached_manager = ConfigurationCache(size)
        cached_manager.update("cat1", "desc1", {'value': {}})
        cached_manager.update("cat2", "desc2", {'value': {}})
        cached_manager.update("cat3", "desc3", {'value': {}})
        cached_manager.update("cat4", "desc4", {'value': {}})
        cached_manager.update("cat5", "desc5", {'value': {}})
        cached_manager.update("cat6", "desc6", {'value': {}})
        cached_manager.update("cat7", "desc7", {'value': {}})
        cached_manager.update("cat8", "desc8", {'value': {}})
        cached_manager.update("cat9", "desc9", {'value': {}})
        cached_manager.update("cat10", "desc10", {'value': {}})
        assert size == cached_manager.size
        keys = list(cached_manager.cache.keys())
        assert cat_names == keys
        if set(cat_miss) & set(cat_names):
            assert False, "Category should not exist in cache manager"

    def test_remove_oldest(self):
        cached_manager = ConfigurationCache()
        cached_manager.max_cache_size = 10
        cached_manager.update("cat1", "desc1", {'value': {}})
        cached_manager.update("cat2", "desc2", {'value': {}})
        cached_manager.update("cat3", "desc3", {'value': {}})
        cached_manager.update("cat4", "desc4", {'value': {}})
        cached_manager.update("cat5", "desc5", {'value': {}})
        cached_manager.update("cat6", "desc6", {'value': {}})
        cached_manager.update("cat7", "desc7", {'value': {}})
        cached_manager.update("cat8", "desc8", {'value': {}})
        cached_manager.update("cat9", "desc9", {'value': {}})
        cached_manager.update("cat10", "desc10", {'value': {}})
        assert 10 == cached_manager.size
        cached_manager.update("cat11", "desc11", {'value': {}})
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
        cached_manager.update("cat1", "desc1", {'value': {}})
        cached_manager.update("cat2", "desc2", {'value': {}})
        cached_manager.update("cat3", "desc3", {'value': {}})
        cached_manager.update("cat4", "desc4", {'value': {}})
        assert 4 == cached_manager.size
        cached_manager.remove("cat2")
        assert 3 == cached_manager.size
        assert 'cat2' not in cached_manager.cache
        assert 'cat1' in cached_manager.cache
        assert 'cat3' in cached_manager.cache
        assert 'cat4' in cached_manager.cache
