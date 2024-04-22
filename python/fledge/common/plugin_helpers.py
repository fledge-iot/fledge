# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

__author__ = "Douglas Orr"
__copyright__ = "Copyright (c) 2020 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

### plugin_helpers -- utility classes to facilitate making python plugins -- ###

import re
import copy

import logging
from fledge.common import iprpc


class HandleMap:
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
        return {"id": _handle_id, "config": copy.deepcopy(config)}

    def get_handle(self, h):
        """ get_handle -- use the unique id to find the real handle """
        return self.handles.get(h["id"], None)

    def del_handle(self, h):
        """ del_handle -- done with the handle, delete the id (which deletes the underlying handle) """
        if h["id"] in self.handles:
            del self.handles[h["id"]]


class PluginHandle(object):
    """ PluginHandle -- utility class that makes converting from config to internal handle easier """

    typefns = {
        "integer": int,
        "float": float,
        "bool": lambda x: x == "true",
        "boolean": lambda x: x == "true",
        "string": str,
        "enumeration": str,
    }

    def __init__(self, service_name, cbinfo=(None, None)):
        # for filter plugins save the info that will be sent to the filter_ingest callback
        self.ingest_ref, self.callback = cbinfo

    def config_update(self, udict):
        """ config_update - store config values in the (derived) handle """

        def snake_case(name):
            # handle member names use snake-case, convert from camel-case
            return re.sub(r"(['A-Z'])", r"_\1", name).lower()

        def get_typed_value(k):
            # auto-convert string config entries into their appropriate type
            _t = udict[k]["type"]
            # "typefns" convert to real type; default type fn assumes identity (string, usually)
            def ident_fn(x): return x
            _typefn = ident_fn if _t not in PluginHandle.typefns else PluginHandle.typefns[_t]
            return _typefn(udict[k]["value"])

        for k in udict.keys():
            _v = get_typed_value(k)
            setattr(self, snake_case(k), _v)

    def rpc_setup(self, config, module_dir="", restart_rpc=False):
        """ rpc_setup -- create a new IPC server configuration, optionally (re)starting the IPC server """
        _server_module = getattr(self, "RPC_SERVER_NAME", None)

        if _server_module is None:
            raise ValueError(
                "RPC_SERVER_NAME class variable must be set to the name of the RPC server module"
            )

        # create the server that does the signal processing on frame data
        if self.rpc is None or restart_rpc:
            self.rpc = iprpc.IPCModuleClient(_server_module, module_dir)
        self.rpc.plugin_init(self._rpc_config())

    def _rpc_config(self):
        """ _rpc_config -- return the dict of k,v to be updated in the server when rpc configuration changes """

        # BY CONVENTION, RPC_PARAMS is the slot which has the names of config members to be sent to
        # the rpc server as config values

        _params = getattr(self, "RPC_CONFIG_MEMBERS", [])
        return {k: getattr(self, k) for k in _params}

    def shutdown(self):
        if self.rpc is not None:
            self.rpc.plugin_shutdown()


class PluginRPCServer(iprpc.InterProcessRPC):
    """ PluginRPCServer - helper class that simplifies writing iprpc server-based plugins """

    def __init__(self, service_name):
        super().__init__()

    def config_update(self, config):
        # servers receive unpickled dict's with typed values
        for k, v in config.items():
            setattr(self, k, v)
