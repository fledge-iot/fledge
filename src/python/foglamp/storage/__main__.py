#!/usr/bin/env python3

# -*- coding: utf-8 -*-

""" This module is for test purpose only!

This must go away when tests and actually STORAGE layer (FOGL-197) are in place

"""

import json
from collections import OrderedDict

from foglamp.core.service_registry.service_registry import Service

from foglamp.storage.storage import Storage, Readings
from foglamp.storage.exceptions import *

# register the service to test the code
Service.Instances.register(name="store", s_type="Storage", address="0.0.0.0", port=8080)


def insert_data():
    data = dict()

    data['key'] = 'SENT_test'
    data['history_ts'] = 'now'
    data['value'] = 1

    con = Storage().connect()
    con.insert_into_tbl("statistics_history", json.dumps(data))
    con.disconnect()


def update_data():
    condition = dict()

    condition['column'] = 'key'
    condition['condition'] = '='
    condition['value'] = 'SENT_test'

    values = dict()
    values['value'] = 444

    data = dict()
    data['condition'] = condition
    data['values'] = values

    con = Storage().connect()
    con.update_tbl("statistics_history", json.dumps(data))
    con.disconnect()


def delete_tbl_data():

    # payload as per doc,
    # see: Plugin Common Delete
    del_cond = dict()
    del_cond['column'] = 'id'
    del_cond['condition'] = '='
    del_cond['value'] = '13057'

    # how to join these AND/ OR conditions?
    and_del_cond = dict()
    and_del_cond['column'] = 'key'
    and_del_cond['condition'] = '='
    and_del_cond['value'] = 'SENT_test'
    # same as where?

    Storage().connect().delete_from_tbl("statistics_history", json.dumps(del_cond))
    Storage().disconnect()


def query_table():
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


def query_table_with_payload():
    x_where_cond = "WHERE key != 'SENSORS'"
    # how are we going to handle AND / OR

    where = OrderedDict()
    where['column'] = 'key'
    where['condition'] = '!='
    where['value'] = 'SENSORS'

    and_where = OrderedDict()
    and_where['column'] = 'ts'
    and_where['condition'] = '>'
    and_where['value'] = ''  # ts value

    # this fails
    # where["and"] = and_where

    aggregate = OrderedDict()
    aggregate['operation'] = 'avg'
    aggregate['column'] = 'temprature'

    query_payload = OrderedDict()
    query_payload['where'] = where
    # query_payload['aggregate'] = aggregate

    payload = json.dumps(query_payload)
    print(payload)

    with Storage() as conn:
        res = conn.query_tbl_with_payload('configuration', payload)
    print(res)

    # check ?

    order_by = ""
    limit = ""
    offset = ""


try:

    query_table()

    insert_data()
    # what happens on conflict?

    update_data()

    delete_tbl_data()
    # returns 400

    query_table_with_payload()

except InvalidServiceInstance as ex:
    print(ex.code, ex.message)
except StorageServiceUnavailable as ex:
    print(ex.code, ex.message)
