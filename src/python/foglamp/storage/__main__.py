#!/usr/bin/env python3

# -*- coding: utf-8 -*-

""" This module is for test purpose only!

This must go away when tests and actually STORAGE layer (FOGL-197) are in place

"""

from foglamp.core.service_registry.service_registry import Service

from foglamp.storage.storage import Storage, Readings
from foglamp.storage.exceptions import *

# register the service to test the code
Service.Instances.register(name="store", s_type="Storage", address="0.0.0.0", port=8080)

# discover the Storage type the service: how do we know the instance name?
# with type there can be multiple instances
# TODO: do get via REST api
try:
    # manually disconnect
    conn1 = Storage().connect()
    Readings.append(conn1, readings=["a", "b"])
    Storage().disconnect()

    # with context
    with Storage() as conn2:
        Readings.append(conn2, readings=["c", "d"])

    with Storage() as conn:
        res = conn.query_tbl('configuration', 'key=COAP_CONF')
        print(res)

    with Storage() as conn:
        # res = conn.query_tbl('configuration') fails
        # should it not be SELECT *
        # or pass "1=1" :]

        query = dict()
        query['key'] = 'COAP_CONF'

        # ASK about approach
        query['blah'] = 'SENSORS'
        query_params = '?'
        for k, v in query.items():
            if not query_params == "?":
                query_params += "&"
            query_params += '{}={}'.format(k, v)
        print("CHECK:", query_params)

        q = 'key=COAP_CONF'
        res = conn.query_tbl('configuration', q)
        print(res)

        import json
        from collections import OrderedDict

        x_where_cond = "WHERE key != 'SENSORS'"
        # how are we going to handle AND / OR

        where = OrderedDict()
        where['column'] = 'key'
        where['condition'] = '!='
        where['value'] = 'SENSORS'

        and_where = OrderedDict()
        where['column'] = 'key'
        where['condition'] = '='
        where['value'] = 'CoAP'

        # this fails
        # where["and"] = and_where

        whr_cond = OrderedDict()
        whr_cond['where'] = where

        aggregate = OrderedDict()
        aggregate['operation'] = 'avg'
        aggregate['column'] = 'temprature'

        query_payload = whr_cond
        # query_payload['aggregate'] = aggregate

        payload = json.dumps(query_payload)
        print(payload)

        res = conn.query_tbl_with_payload('configuration', payload)
        print(res)

        # check ?

        order_by = ""
        limit = ""
        offset = ""

except InvalidServiceInstance as ex:
    print(ex.code, ex.message)
except StorageServiceUnavailable as ex:
    print(ex.code, ex.message)
