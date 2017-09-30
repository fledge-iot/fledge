# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Storage layer python client
"""

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import urllib.parse
import json
from collections import OrderedDict
from foglamp import logger

_LOGGER = logger.setup(__name__)


class PayloadBuilder(object):
    """ Payload Builder to be used in Python wrapper class for Storage Service
    Ref: https://docs.google.com/document/d/1qGIswveF9p2MmAOw_W1oXpo_aFUJd3bXBkW563E16g0/edit#
    Ref: http://json-schema.org/

    TODO: Add json validator feature directly from json schema.
          Ref: http://json-schema.org/implementations.html#validators
    """

    # TODO: Add tests

    query_payload = OrderedDict()
    
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
    def UPDATE(cls, **kwargs):
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
        return json.dumps(cls.query_payload)

    @classmethod
    def query_params(cls):
        where = cls.query_payload['where']
        query_params = {where['column']: where['value']}
        for key, value in where.items():
            if key == 'and':
                query_params.update({value['column']: value['value']})
        return urllib.parse.urlencode(query_params)

if __name__ == "__main__":
    PayloadBuilder.query_payload = OrderedDict()
    # Select
    sql = PayloadBuilder.\
        SELECT('id', 'type', 'repeat', 'process_name').\
        FROM('schedules').\
        WHERE(['id', '=', 'test']).\
        AND_WHERE(['process_name', '=', 'test']). \
        OR_WHERE(['process_name', '=', 'sleep']).\
        LIMIT(3).\
        GROUP_BY('process_name', 'id').\
        ORDER_BY(['process_name', 'desc']).\
        AGGREGATE(['count', 'process_name']).\
        payload()
    print(sql)

    PayloadBuilder.query_payload = OrderedDict()
    # Insert
    sql = PayloadBuilder.\
        INSERT_INTO('schedules').\
        INSERT(id='test', process_name='sleep', type=3, repeat=45677).\
        payload()
    print(sql)

    PayloadBuilder.query_payload = OrderedDict()
    # Update
    sql = PayloadBuilder.\
        UPDATE_TABLE('schedules').\
        UPDATE(id='test', process_name='sleep', type=3, repeat=45677).\
        WHERE(['id', '=', 'test']). \
        payload()
    print(sql)

    from foglamp.core.service_registry.service_registry import Service
    from foglamp.storage.storage import Storage

    Service.Instances.register(name="store", s_type="Storage", address="0.0.0.0", port=8080)

    PayloadBuilder.query_payload = OrderedDict()
    sql = PayloadBuilder.WHERE(["key", "=", "CoAP"]).payload()
    tbl_name = 'configuration'
    q = sql
    print(sql)
    print(Storage().query_tbl_with_payload(tbl_name, q))

    PayloadBuilder.query_payload = OrderedDict()
    # sql = pb.WHERE(["key", "=", "COAP_CONF"]).\
    # AND_WHERE(["ts", "=", "2017-09-15 12:33:22.619847+05:30"]).query_params()
    sql = PayloadBuilder.WHERE(["key", "=", "CoAP"]).query_params()
    print(sql)
    tbl_name = 'configuration'
    print(Storage().query_tbl(tbl_name, sql))
