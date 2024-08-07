# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import json
from fledge.common.logger import FLCoreLogger

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2024, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = FLCoreLogger().get_logger(__name__)

DEFAULT_CONFIG = {
                'allowedIP': {
                    'description': 'A list of allowed IP addresses',
                    'type': 'list',
                    'items': 'string',
                    'default': "[]",
                    'displayName': 'Allowed IP Addresses',
                    'order': '1',
                    'permissions': ['admin']
                },
                'deniedIP': {
                    'description': 'A list of denied IP addresses',
                    'type': 'list',
                    'items': 'string',
                    'default': "[]",
                    'displayName': 'Denied IP Addresses',
                    'order': '2',
                    'permissions': ['admin']
                }
            }


class Firewall:
    """ Monitor and Control HTTP Network Traffic """

    __slots__ = ['category', 'display_name', 'description', 'config']

    def __init__(self):
        self.category = 'firewall'
        self.display_name = 'Firewall'
        self.description = 'Monitor and Control HTTP Network Traffic'
        self.config = DEFAULT_CONFIG

    def __repr__(self):
        template = ('Firewall settings: <category={s.category}, display_name={s.display_name}, '
                    'description={s.description}, config={s.config}>')
        return template.format(s=self)

    def __str__(self):
        return self.__repr__()

    class IPAddresses:

        @classmethod
        def get(cls) -> dict:
            # To avoid cyclic import
            from fledge.services.core import server
            return server.Server._firewall_ip_addresses

        @classmethod
        def save(cls, data: dict) -> None:
            # To avoid cyclic import
            from fledge.services.core import server
            if 'allowedIP' in data:
                server.Server._firewall_ip_addresses.update({'allowedIP': json.loads(data['allowedIP']['value'])})
            if 'deniedIP' in data:
                server.Server._firewall_ip_addresses.update({'deniedIP': json.loads(data['deniedIP']['value'])})

        @classmethod
        def clear(cls) -> None:
            # To avoid cyclic import
            from fledge.services.core import server
            server.Server._firewall_ip_addresses = {}

