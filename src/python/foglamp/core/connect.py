# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


from foglamp.microservice_management.service_registry.service_registry import Service
from foglamp.storage.storage import Storage
from foglamp import logger

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


# _logger = logger.setup(__name__, level=20)
_logger = logger.setup(__name__)


# TODO: Needs refactoring or better way to allow global discovery in core process
def get_storage():
    """ Storage Object """
    try:
        services = Service.Instances.get(name="FogLAMP Storage")
        storage_svc = services[0]
        _storage = Storage(core_management_host=None, core_management_port=None, svc=storage_svc)
        # _logger.info(type(_storage))
    except Exception as ex:
        _logger.exception(str(ex))
        raise
    return _storage
