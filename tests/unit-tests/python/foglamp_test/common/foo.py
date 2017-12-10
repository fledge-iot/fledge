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

    def unregister(self):
        res = self.unregister_service()
        try:
            sid = res["id"]
            # log service with <sid> unregistered
        except KeyError:
            error = res["error"]
            # log the error
        except Exception as ex:
            reason = str(ex)
        return res

    def find_services(self, name=None, _type=None):
        res = self.get_service(name, _type)
        try:
            services = res["services"]
        except KeyError:
            error = res["error"]
            # log the error
        except Exception as ex:
            reason = str(ex)
        return res


def get_instance(name, host, port):
    sys.argv = ['./foo.py', '--name={}'.format(name), '--address={}'.format(host), '--port={}'.format(port)]
    # print(sys.argv)
    fs = FooServer()
    return fs


