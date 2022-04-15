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

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2022 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


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
    get_svc_conn = http.client.HTTPConnection("{}:{}".format(core_management_host, core_management_port))
    get_svc_conn.request("GET", '/fledge/service')
    r = get_svc_conn.getresponse()
    res = r.read().decode()
    svc_jdoc = json.loads(res)
    write_payload = {}
    for svc in svc_jdoc['services']:
        if svc['type'] == "Core":
            # find the content of script category for write operation
            get_script_cat_conn = http.client.HTTPConnection("{}:{}".format(svc['address'], svc['service_port']))
            get_script_cat_conn.request("GET", '/fledge/category/{}'.format(script_name))
            r = get_script_cat_conn.getresponse()
            res = r.read().decode()
            script_cat_jdoc = json.loads(res)
            write_payloads = json.loads(script_cat_jdoc['write']['value'])
            for wp in write_payloads:
                write_payload.update(wp['values'])
            break

    for svc in svc_jdoc['services']:
        if svc['type'] == "Dispatcher":
            # Call dispatcher write API with payload
            post_dispatch_conn = http.client.HTTPConnection("{}:{}".format(svc['address'], svc['service_port']))
            data = {"destination": "script", "name": script_name, "write": write_payload}
            post_dispatch_conn.request('POST', '/dispatch/write', json.dumps(data))
            r = post_dispatch_conn.getresponse()
            res = r.read().decode()
            write_dispatch_jdoc = json.loads(res)
            _logger.info("For script category with name: {}, dispatcher write API response: {}".format(
                script_name, write_dispatch_jdoc))
            break
