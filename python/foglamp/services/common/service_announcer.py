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
        host = self.get_ip()
        service_name = "{}.{}".format(sname, stype)
        desc_txt = 'FogLAMP Service'
        if isinstance(txt, list):
            try:
                desc_txt = txt[0]
            except:
                pass
        desc = {'description': desc_txt}
        """ Create a service description.
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
            stype,
            service_name,
            socket.inet_aton(host),
            port,
            properties=desc,
            server="{}.local.".format(host_name)
        )
        zeroconf = Zeroconf()
        zeroconf.register_service(info, allow_name_change=True)

    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip
