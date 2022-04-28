#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Automation script starter"""

import logging
import json
import http.client
import argparse
from fledge.common import logger


if __name__ == '__main__':
    _logger = logger.setup("Automation Script", level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--address", required=True)
    parser.add_argument("--port", required=True, type=int)
    namespace, args = parser.parse_known_args()
    script_name = getattr(namespace, 'name')
    core_management_host = getattr(namespace, 'address')
    core_management_port = getattr(namespace, 'port')
    # Get services list
    conn = http.client.HTTPConnection("{}:{}".format(core_management_host, core_management_port))
    conn.request("GET", '/fledge/service')
    r = conn.getresponse()
    r = r.read().decode()
    svc_jdoc = json.loads(r)
    for svc in svc_jdoc['services']:
        if svc['type'] == "Dispatcher":
            # Call dispatcher write API
            conn = http.client.HTTPConnection("{}:{}".format(svc['address'], svc['service_port']))
            # If any parameter substitution then pass at run time in write payload
            data = {"destination": "script", "name": script_name, "write": {}}
            conn.request('POST', '/dispatch/write', json.dumps(data))
            r = conn.getresponse()
            res = r.read().decode()
            response = json.loads(res)
            _logger.info("For script category with name: {},  dispatcher write API response: {}".format(script_name,
                                                                                                        response))
            break
