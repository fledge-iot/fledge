#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from foglamp.services.common.microservice import FoglampProcess


class FooServer(FoglampProcess):

    def __init__(self):
        super().__init__()

    def run(self):
        pass


def get_instance(name, host, port):
    sys.argv = ['./foo.py', '--name={}'.format(name), '--address={}'.format(host), '--port={}'.format(port)]
    fs = FooServer()
    return fs
