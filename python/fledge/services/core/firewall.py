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


class Singleton(object):
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state


class Firewall(Singleton):
    """ Monitor and Control HTTP Network Traffic """

    __slots__ = ['category', 'display_name', 'description', 'config', 'ip_addresses']

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

    def __init__(self):
        super().__init__()

        self.category = 'firewall'
        self.display_name = 'Firewall'
        self.description = 'Monitor and Control HTTP Network Traffic'
        self.config = self.DEFAULT_CONFIG
        self.ip_addresses = {}

    def __repr__(self):
        template = ('Firewall settings: <category={s.category}, display_name={s.display_name}, '
                    'description={s.description}, config={s.config}, ip_addresses={s.ip_addresses}>')
        return template.format(s=self)

    def __str__(self):
        return self.__repr__()

    @classmethod
    def get_instance(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
        return cls._instance

    class IPAddresses:

        @classmethod
        def get(cls) -> dict:
            f = Firewall.get_instance()
            return f.ip_addresses

        @classmethod
        def save(cls, data: dict) -> None:
            f = Firewall.get_instance()
            if 'allowedIP' in data:
                f.ip_addresses.update({'allowedIP': json.loads(data['allowedIP']['value'])})
            if 'deniedIP' in data:
                f.ip_addresses.update({'deniedIP': json.loads(data['deniedIP']['value'])})

        @classmethod
        def clear(cls) -> None:
            f = Firewall.get_instance()
            f.ip_addresses = {}

