# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Storage layer python client payload builder
"""

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

from collections import OrderedDict
import json
import urllib.parse

from foglamp import logger


_LOGGER = logger.setup(__name__)


class PayloadBuilder(object):
    """ Payload Builder to be used in Python client  for Storage Service

    """

    # TODO: Add json validator
    ''' Ref: https://docs.google.com/document/d/1qGIswveF9p2MmAOw_W1oXpo_aFUJd3bXBkW563E16g0/edit#
        Ref: http://json-schema.org/
        Ref: http://json-schema.org/implementations.html#validators
    '''
    # TODO: Add tests

    query_payload = None

    def __init__(self):
        self.__class__.query_payload = OrderedDict()

    @staticmethod
    def verify_condition(arg):
        retval = False
        if isinstance(arg, list):
            if len(arg) == 3:
                # TODO: Implement LIKE and IN later when support becomes available in storage service
                if arg[1] in ['<', '>', '=', '>=', '<=', '!=']:
                    retval = True
        return retval

    @staticmethod
    def verify_aggregation(arg):
        retval = False
        if isinstance(arg, list):
            if len(arg) == 2:
                if arg[0] in ['min', 'max', 'avg', 'sum', 'count']:
                    retval = True
        return retval

    @staticmethod
    def verify_orderby(arg):
        retval = False
        if isinstance(arg, list):
            if len(arg) == 2:
                if arg[1].upper() in ['ASC', 'DESC']:
                    retval = True
        return retval

    @classmethod
    def SELECT(cls, *args):
        if len(args) > 0:
            cls.query_payload.update({"columns": ','.join(args)})
        return cls

    @classmethod
    def SELECT_ALL(cls, *args):
        return cls

    @classmethod
    def FROM(cls, tbl_name):
        cls.query_payload.update({"table": tbl_name})
        return cls

    @classmethod
    def UPDATE_TABLE(cls, tbl_name):
        return cls.FROM(tbl_name)

    @classmethod
    def COLS(cls, kwargs):
        values = {}
        for key, value in kwargs.items():
            values.update({key: value})
        return values

    @classmethod
    def SET(cls, **kwargs):
        cls.query_payload.update({"values": cls.COLS(kwargs)})
        return cls

    @classmethod
    def INSERT(cls, **kwargs):
        cls.query_payload.update(cls.COLS(kwargs))
        return cls

    @classmethod
    def INSERT_INTO(cls, tbl_name):
        return cls.FROM(tbl_name)

    @classmethod
    def DELETE(cls, tbl_name):
        return cls.FROM(tbl_name)

    @classmethod
    def WHERE(cls, arg):
        condition = {}
        if cls.verify_condition(arg):
            condition.update({"column": arg[0], "condition": arg[1], "value": arg[2]})
            cls.query_payload.update({"where": condition})
        return cls

    @classmethod
    def AND_WHERE(cls, *args):
        for arg in args:
            condition = {}
            if cls.verify_condition(arg):
                condition.update({"column": arg[0], "condition": arg[1], "value": arg[2]})
                cls.query_payload["where"].update({"and": condition})
        return cls

    @classmethod
    def OR_WHERE(cls, *args):
        for arg in args:
            if cls.verify_condition(arg):
                condition = {}
                condition.update({"column": arg[0], "condition": arg[1], "value": arg[2]})
                cls.query_payload["where"].update({"or": condition})
        return cls

    @classmethod
    def GROUP_BY(cls, *args):
        cls.query_payload.update({"group": ', '.join(args)})
        return cls

    @classmethod
    def AGGREGATE(cls, *args):
        for arg in args:
            aggregate = {}
            if cls.verify_aggregation(arg):
                aggregate.update({"operation": arg[0], "column": arg[1]})
                if 'aggregate' in cls.query_payload:
                    if isinstance(cls.query_payload['aggregate'], list):
                        cls.query_payload['aggregate'].append(aggregate)
                    else:
                        cls.query_payload['aggregate'] = list(cls.query_payload.get('aggregate'))
                        cls.query_payload['aggregate'].append(aggregate)
                else:
                    cls.query_payload.update({"aggregate": aggregate})
        return cls

    @classmethod
    def HAVING(cls):
        # TODO: To be implemented
        return cls

    @classmethod
    def LIMIT(cls, arg):
        if isinstance(arg, int):
            cls.query_payload.update({"limit": arg})
        return cls

    @classmethod
    def OFFSET(cls, arg):
        if isinstance(arg, int):
            try:
                limit = cls.query_payload['limit']
            except KeyError:
                raise KeyError("LIMIT is required to set OFFSET to skip")
            cls.query_payload.update({"skip": arg})
        return cls

    SKIP = OFFSET

    @classmethod
    def ORDER_BY(cls, *args):
        for arg in args:
            sort = {}
            if cls.verify_orderby(arg):
                sort.update({"column": arg[0], "direction": arg[1]})
                if 'sort' in cls.query_payload:
                    if isinstance(cls.query_payload['sort'], list):
                        cls.query_payload['sort'].append(sort)
                    else:
                        cls.query_payload['sort'] = list(cls.query_payload.get('sort'))
                        cls.query_payload['sort'].append(sort)
                else:
                    cls.query_payload.update({"sort": sort})
        return cls

    @classmethod
    def payload(cls):
        return json.dumps(cls.query_payload, sort_keys=True)

    @classmethod
    def query_params(cls):
        where = cls.query_payload['where']
        query_params = {where['column']: where['value']}
        for key, value in where.items():
            if key == 'and':
                query_params.update({value['column']: value['value']})
        return urllib.parse.urlencode(query_params)


if __name__ == "__main__":

    # TODO: remove once self registration is done
    from foglamp.core.service_registry.service_registry import Service
    from foglamp.storage.storage import Storage

    Service.Instances.register(name="store", s_type="Storage", address="0.0.0.0", port=8080)

    # Select
    _w_payload = PayloadBuilder().WHERE(["key", "=", "CoAP"]).payload()
    print(_w_payload, '\n')
    print(Storage().query_tbl_with_payload('configuration', _w_payload))
    print('\n')

    _w_query_params = PayloadBuilder().WHERE(["key", "=", "CoAP"]).query_params()
    print(_w_query_params, '\n')
    print(Storage().query_tbl('configuration', _w_query_params))
    print('\n')

    complex_payload = PayloadBuilder()\
        .SELECT('id', 'type', 'repeat', 'process_name')\
        .FROM('schedules')\
        .WHERE(['id', '=', 'test'])\
        .AND_WHERE(['process_name', '=', 'test'])\
        .OR_WHERE(['process_name', '=', 'sleep'])\
        .LIMIT(3)\
        .GROUP_BY('process_name', 'id')\
        .ORDER_BY(['process_name', 'desc'])\
        .AGGREGATE(['count', 'process_name'])\
        .payload()

    print(complex_payload, '\n')

    # TODO: Test above complex payload
    # 1) FROM is not needed, as we pass table table name
    # 2) Check: SELECT col1, col2 FROM tbl support i.e. specific columns
    # 3) assert with expected payload

    # Insert
    insert_payload = PayloadBuilder()\
        .INSERT(key='SENT_pb', history_ts='now', value='11')\
        .payload()
    print(insert_payload, '\n')

    insert_test_data = OrderedDict()
    insert_test_data['key'] = 'SENT_pb'
    insert_test_data['history_ts'] = 'now'
    insert_test_data['value'] = '11'

    assert insert_payload == json.dumps(insert_test_data, sort_keys=True)

    res = Storage().insert_into_tbl("statistics_history", insert_payload)
    print(res)
    # assert res  "{'response': 'inserted'}"

    # Update
    update_payload = PayloadBuilder()\
        .SET(value=22)\
        .WHERE(['key', '=', 'SENT_pb'])\
        .payload()
    print(update_payload, '\n')

    # update test data dict sample
    condition = dict()
    condition['column'] = 'key'
    condition['condition'] = '='
    condition['value'] = 'SENT_pb'

    values = dict()
    values['value'] = 22

    update_test_data = dict()
    # update_test_data['condition'] = condition # also works!
    update_test_data['where'] = condition
    update_test_data['values'] = values

    assert update_payload == json.dumps(update_test_data, sort_keys=True)

    res = Storage().update_tbl("statistics_history", update_payload)
    print(res)
    # assert res  "{'response': 'updated'}"

    try:
        offset = PayloadBuilder().SKIP(5).payload()
        print(offset)
    except Exception as ex:
        print(str(ex))

    limit = PayloadBuilder().LIMIT(2).payload()
    print(limit)

    limit_and_offset = PayloadBuilder().LIMIT(2).OFFSET(10).payload()
    print(limit_and_offset)

    limit_and_skip = PayloadBuilder().LIMIT(2).SKIP(12).payload()
    print(limit_and_skip)
