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
    del_cond['value'] = '13081'

    # join these AND/ OR conditions
    del_cond_2 = dict()
    del_cond_2['column'] = 'key'
    del_cond_2['condition'] = '='
    del_cond_2['value'] = 'SENT_test'

    # same as where
    cond = dict()
    cond['where'] = del_cond

    ''' DELETE FROM statistics_history WHERE key = 'SENT_test' AND id='13084' '''
    cond['and'] = del_cond_2

    ''' DELETE FROM statistics_history WHERE key = 'SENT_test' OR id='13084' '''
    cond['or'] = del_cond_2

    res = Storage().connect().delete_from_tbl("statistics_history", json.dumps(cond))
    print(res)
    Storage().disconnect()

    ''' DELETE FROM statistics_history '''
    # res = Storage().connect().delete_from_tbl("statistics_history")
    # print(res)
    # Storage().disconnect()


def query_table():

    with Storage() as conn:
        # commented code
        '''
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
        '''

        ''' SELECT * FROM configuration WHERE key='COAP_CONF' '''
        # TODO: check &limit=1 (and offset, order_by) will work here?
        q = 'key=COAP_CONF'
        res = conn.query_tbl('configuration', q)
        print(res)

        ''' SELECT * FROM statistics '''
        res = conn.query_tbl('statistics')
        print(res)


def query_table_with_payload():

    # WHERE key = 'SENT_test'"

    where = OrderedDict()
    where['column'] = 'key'
    where['condition'] = '='
    where['value'] = 'SENT_test'

    # verify AND / OR?
    where_2 = OrderedDict()
    where_2['column'] = 'value'
    where_2['condition'] = '='
    where_2['value'] = '444'

    aggregate = OrderedDict()
    aggregate['operation'] = 'min'
    aggregate['column'] = 'value'

    query_payload = OrderedDict()
    query_payload['where'] = where_2
    # query_payload['and'] = where_2
    # query_payload['or'] = where_2
    # query_payload['aggregate'] = aggregate

    # query_payload['limit'] = 2
    # query_payload['skip'] = 1

    # check ?
    order_by = ""

    payload = json.dumps(query_payload)
    print(payload)

    with Storage() as conn:
        res = conn.query_tbl_with_payload('statistics_history', payload)
    print(res)


try:

    query_table()

    insert_data()
    # what happens on conflict?

    update_data()

    delete_tbl_data()

    query_table_with_payload()

except InvalidServiceInstance as ex:
    print(ex.code, ex.message)
except StorageServiceUnavailable as ex:
    print(ex.code, ex.message)
