# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from fledge.common.logger import FLCoreLogger
from fledge.common.storage_client.storage_client import StorageClientAsync, ReadingsStorageClientAsync
from fledge.services.core.service_registry.service_registry import ServiceRegistry

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = FLCoreLogger().get_logger(__name__)


# TODO: Needs refactoring or better way to allow global discovery in core process
def get_storage_async():
    """ Storage Object """
    try:
        services = ServiceRegistry.get(name="Fledge Storage")
        storage_svc = services[0]
        _storage = StorageClientAsync(core_management_host=None, core_management_port=None, svc=storage_svc)
    except Exception as ex:
        _logger.error(ex)
        raise
    return _storage


# TODO: Needs refactoring or better way to allow global discovery in core process
def get_readings_async():
    """ Storage Object """
    try:
        services = ServiceRegistry.get(name="Fledge Storage")
        storage_svc = services[0]
        _readings = ReadingsStorageClientAsync(core_mgt_host=None, core_mgt_port=None, svc=storage_svc)
    except Exception as ex:
        _logger.error(ex)
        raise
    return _readings
