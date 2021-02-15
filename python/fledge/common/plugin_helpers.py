# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge.readthedocs.io/
# FLEDGE_END

__author__ = "Douglas Orr"
__copyright__ = "Copyright (c) 2020 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

### plugin_helpers -- utility classes to facilitate making python plugins -- ###

import re
import copy

class HandleMap():
    # keep a map of json-able handles to internal objects that have the working instance state
    def __init__(self, name):
        self.name = name
        self.uid = 0
        self.handles = {}
        
    def new_handle(self, handle, config):
        """ new_handle -- make a new entry in our handle map findable by id; stash a copy of current config """
        _handle_id = "{}-{}".format(self.name, self.uid)
        self.uid += 1
        self.handles[_handle_id] = handle
        return { 'id': _handle_id, 'config': copy.deepcopy(config) }

    def get_handle(self, h):
        """ get_handle -- use the unique id to find the real handle """
        return self.handles.get(h['id'], None)

    def del_handle(self, h):
        """ del_handle -- done with the handle, delete the id (which deletes the underlying handle) """
        if h['id'] in self.handles:
            del self.handles[h['id']]

class PluginHandle(object):
    """ PluginHandle -- utility class that makes converting from config to internal handle easier """
    typefns = {
        'int': int,
        'integer': int,
        'float': float,
        'bool': lambda x: x == 'true',
        'boolean': lambda x: x == 'true',
        'string': str,
        'str': str,
        'enumeration': str,
    }
        
    def config_update(self, udict):
        """ config_update - store config values in the (derived) handle """
        
        def snake_case(name):
            # handle member names use snake-case, convert from camel-case
            return re.sub(r"(['A-Z'])", r"_\1", name).lower()

        def get_typed_value(k):
            # auto-convert string config entries into their appropriate type
            _t = udict[k]['type']
            return PluginHandle.typefns[_t](udict[k]['value'])

        for k in udict.keys():
            _v = get_typed_value(k)
            setattr(self, snake_case(k), _v)

        
