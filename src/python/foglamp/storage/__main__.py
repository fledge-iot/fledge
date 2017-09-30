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
    where_2['condition'] = '>'
    where_2['value'] = '444'

    aggregate = OrderedDict()
    aggregate['operation'] = 'min'
    aggregate['column'] = 'value'

    query_payload = OrderedDict()
    query_payload['where'] = where_2
    query_payload['and'] = where_2
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


def append_readings():
    import uuid
    import random
    readings = []

    def map_reading(asset_code, reading, read_key=None, user_ts=None):
        read = dict()
        read['asset_code'] = asset_code
        print(read_key)
        read['read_key'] = read_key
        read['reading'] = dict()
        read['reading']['rate'] = reading
        read['user_ts'] = "2017-09-21 15:00:09.025655"
        # ingest 2017-01-02T01:02:03.23232Z-05:00
        # asset, key, reading, timestamp
        # storage 2017-09-21 15:00:09.025655
        # asset_code, read_key, reading, user_ts
        return read
    x = str(uuid.uuid4())
    # to use duplicate read_key uuid (ON CONFLICT DO NOTHING)
    for _ in range(1, 2):
        readings.append(map_reading('MyAsset', random.uniform(1.0, 100.1), read_key=str(uuid.uuid4())))

    payload = dict()
    payload['readings'] = readings

    print(json.dumps(payload))

    r = Readings().connect()
    res = r.append(json.dumps(payload))
    print(res)
    Readings().disconnect()


def fetch_readings():
    print("fetch_readings:")
    r = Readings().connect()
    # tested,
    # works fine if records are less then count
    # also works fine if reading_id does not exist, {'rows': [], 'count': 0}
    res = r.fetch(reading_id=1, count=2)
    print(res)
    Readings().disconnect()


def purge_readings():
    print("purge_readings:")

    r = Readings().connect()

    res = r.purge('24', '100071')

    # TODO: Move to tests :]
    # try many (type checking)

    res = r.purge(24, '100071')

    res = r.purge(24, '100071', 'puRge')

    res = r.purge(24, '100071', 'RETAIN')

    try:
        # res = r.purge('b', '100071', 'RETAIN')

        # res = r.purge('1', 'v', 'RETAIN')

        res = r.purge(24, '100071', 'xRETAIN')
    except ValueError:
        print("age or reading is not an integer value :/")
    except InvalidReadingsPurgeFlagParameters:
        print("AS expected, InvalidReadingsPurgeFlagParameters")

    print(res)
    Readings().disconnect()


def query_readings():

    cond1 = OrderedDict()
    cond1['column'] = 'asset_code'
    cond1['condition'] = '='
    cond1['value'] = 'MyAsset'

    query_payload = OrderedDict()
    query_payload['where'] = cond1

    query_payload['limit'] = 2

    query_payload['skip'] = 1

    print("query_readings payload: ", json.dumps(query_payload))

    r = Readings().connect()
    res = r.query(json.dumps(query_payload))
    print(res)

    # expected response
    '''{'count': 2, 'rows': [
            {'read_key': 'cdbec41e-9c41-4144-8257-e2ab2242dc76', 'user_ts': '2017-09-21 15:00:09.025655+05:30', 'id': 22, 'reading': {'rate': 92.58901867128075}, 'asset_code': 'MyAsset', 'ts': '2017-09-28 20:18:43.809661+05:30'},
            {'read_key': '6ad3cc76-e859-4c78-8031-91fccbb1a5a9', 'user_ts': '2017-09-21 15:00:09.025655+05:30', 'id': 23, 'reading': {'rate': 24.350853712845392}, 'asset_code': 'MyAsset', 'ts': '2017-09-28 20:19:16.739619+05:30'}
            ]
    }'''

    Readings().disconnect()


try:

    query_table()

    insert_data()

    update_data()

    delete_tbl_data()

    query_table_with_payload()

    append_readings()
    # what happens on conflict?

    fetch_readings()

    # TODO: these value shall be picked from purge config and passed to it?
    purge_readings()

    query_readings()

except InvalidServiceInstance as ex:
    print(ex.code, ex.message)
except StorageServiceUnavailable as ex:
    print(ex.code, ex.message)
