# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Common FledgeMicroservice Class"""


import socket
from zeroconf import ServiceInfo, ServiceBrowser, ServiceStateChange, Zeroconf

from fledge.common import logger


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
        desc_txt = 'Fledge Service'
        if isinstance(txt, list):
            try:
                desc_txt = txt[0]
            except:
                pass
        desc = {'description': desc_txt}
        """ Create a service description.
                type_: fully qualified service type name
                name: fully qualified service name
                port: port that the service runs on
                weight: weight of the service
                addresses: list of IP addresses as unsigned short, network byte order
                priority: priority of the service
                properties: dictionary of properties (or a string holding the
                            bytes for the text field)
                server: fully qualified name for service host (defaults to name)
                host_ttl: ttl used for A/SRV records
                other_ttl: ttl used for PTR/TXT records"""
        info = ServiceInfo(
            stype,
            service_name,
            port,
            addresses=[socket.inet_aton(host)],
            properties=desc,
            server="{}.local.".format(host_name)
        )
        zeroconf = Zeroconf()
        # Refresh zeroconf cache
        # browser = ServiceBrowser(zeroconf, stype, handlers=[self.on_service_state_change])
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

    def on_service_state_change(self, zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange) -> None:
        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
