#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from foglamp.services.common.microservice import FoglampMicroservice


class FooServer(FoglampMicroservice):

    _type = "Southbound"

    def __init__(self):
        super().__init__()

    def run(self):
        pass

    def change(self, request):
        pass

    # def shutdown(self, request):
    def shutdown(self):
        # I have nothing to clean
        return self._core_microservice_management_client.unregister_service(self._microservice_id)


def get_instance(name, host, port):
    sys.argv = ['./foo.py', '--name={}'.format(name), '--address={}'.format(host), '--port={}'.format(port)]
    # print(sys.argv)
    fs = FooServer()
    return fs
