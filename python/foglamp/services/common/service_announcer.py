# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common FoglampMicroservice Class"""


import socket
from zeroconf import ServiceInfo, Zeroconf

from foglamp.common import logger


__author__ = "Mark Riddoch, Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)


class ServiceAnnouncer:
    def __init__(self, sname, stype, port, txt):
        host_name = socket.gethostname()
        host = socket.gethostbyname(host_name)
        service_name = "_" + sname.lower() + "._tcp.local."
        desc = {'path': '/~paulsm/'}  # TODO: Change
        _LOGGER.error(">>>>>>>>>>>>>>>>> %s", service_name)
        """Create a service description.
                type_: fully qualified service type name
                name: fully qualified service name
                address: IP address as unsigned short, network byte order
                port: port that the service runs on
                weight: weight of the service
                priority: priority of the service
                properties: dictionary of properties (or a string holding the
                            bytes for the text field)
                server: fully qualified name for service host (defaults to name)
                host_ttl: ttl used for A/SRV records
                other_ttl: ttl used for PTR/TXT records"""
        info = ServiceInfo(
            "_foglamp-manage._tcp.local.",
            host_name + "._foglamp-manage._tcp.local.",
            socket.inet_aton(host),
            port,
            0,
            0,
            desc,
            "foglamp.local.",
        )
        zeroconf = Zeroconf()
        zeroconf.register_service(info)
