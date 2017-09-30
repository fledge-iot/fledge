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

    def __init__(self, query_payload=OrderedDict()):
        # FIXME: Below line is not working
        # self.query_payload = query_payload
        self.query_payload = OrderedDict()

    schema = None
    with open('jsonschema.json') as data_file:
        schema = json.load(data_file, object_pairs_hook=OrderedDict)

    SCHEMA_TYPE_MAP = {
        "string": str,
        "number": int,
        "integer": int,
        "object": dict,
        "array": list,
        "null": None.__class__,
    }

    @staticmethod
    def find_type(name, my_schema=schema, retval=None, result=list()):
        """
        Recursively searches for 'name' in the given dict of any depth

        :param name:
        :param my_schema:
        :param retval:
        :param result: path of the "name" starting from root, if success else None
        :return:
        """
        for key, value in my_schema.items():
            result.append(key)
            if key == name:
                retval = value['type']
                break
            elif isinstance(value, OrderedDict):
                retval, result = PayloadBuilder.find_type(name, value, retval, result)
        # FIXME: result
        return retval, result

    # TODO: Add tests

    @staticmethod
    def verify_condition(arg):
        retval = False
        if isinstance(arg, list):
            if len(arg) == 3:
                assert isinstance(arg[0], PayloadBuilder.SCHEMA_TYPE_MAP[PayloadBuilder.find_type('where_column')[0]])
                assert isinstance(arg[1], PayloadBuilder.SCHEMA_TYPE_MAP[PayloadBuilder.find_type('where_condition')[0]])
                assert isinstance(arg[2], PayloadBuilder.SCHEMA_TYPE_MAP[PayloadBuilder.find_type('where_value')[0]])
                # TODO: Implement LIKE and IN later when support becomes available in storage service
                if arg[1] in ['<', '>', '=', '>=', '<=', '!=']:
                    retval = True
        return retval

    @staticmethod
    def verify_aggregation(arg):
        retval = False
        if isinstance(arg, list):
            if len(arg) == 2:
                assert isinstance(arg[0], PayloadBuilder.SCHEMA_TYPE_MAP[PayloadBuilder.find_type('aggregate_operation')[0]])
                assert isinstance(arg[1], PayloadBuilder.SCHEMA_TYPE_MAP[PayloadBuilder.find_type('aggregate_column')[0]])
                if arg[0] in ['min', 'max', 'avg', 'sum', 'count']:
                    retval = True
        return retval

    @staticmethod
    def verify_orderby(arg):
        retval = False
        if isinstance(arg, list):
            if len(arg) == 2:
                assert isinstance(arg[0], PayloadBuilder.SCHEMA_TYPE_MAP[PayloadBuilder.find_type('sort_column')[0]])
                assert isinstance(arg[1], PayloadBuilder.SCHEMA_TYPE_MAP[PayloadBuilder.find_type('sort_direction')[0]])
                if arg[1].upper() in ['ASC', 'DESC']:
                    retval = True
        return retval

    def SELECT(self, *args):
        if len(args) > 0:
            self.query_payload.update({"columns": ','.join(args)})
        return self

    def SELECTALL(self, *args):
        return self

    def FROM(self, tbl_name):
        self.query_payload.update({"table": tbl_name})
        return self

    def UPDATE_TABLE(self, tbl_name):
        return self.FROM(tbl_name)

    def COLS(self, kwargs):
        values = {}
        for key, value in kwargs.items():
            values.update({key: value})
        return values

    def UPDATE(self, **kwargs):
        self.query_payload.update({"values": self.COLS(kwargs)})
        return self

    def INSERT(self, **kwargs):
        self.query_payload.update(self.COLS(kwargs))
        return self

    def INSERT_INTO(self, tbl_name):
        return self.FROM(tbl_name)

    def DELETE(self, tbl_name):
        return self.FROM(tbl_name)

    def WHERE(self, arg):
        condition = {}
        if self.verify_condition(arg):
            condition.update({"column": arg[0], "condition": arg[1], "value": arg[2]})
            self.query_payload.update({"where": condition})
        return self

    def AND_WHERE(self, *args):
        for arg in args:
            condition = {}
            if self.verify_condition(arg):
                condition.update({"column": arg[0], "condition": arg[1], "value": arg[2]})
                self.query_payload["where"].update({"and": condition})
        return self

    def OR_WHERE(self, *args):
        for arg in args:
            if self.verify_condition(arg):
                condition = {}
                condition.update({"column": arg[0], "condition": arg[1], "value": arg[2]})
                self.query_payload["where"].update({"or": condition})
        return self

    def GROUP_BY(self, *args):
        self.query_payload.update({"group": ', '.join(args)})
        return self

    def AGGREGATE(self, *args):
        for arg in args:
            aggregate = {}
            if self.verify_aggregation(arg):
                aggregate.update({"operation": arg[0], "column": arg[1]})
                if 'aggregate' in self.query_payload:
                    if isinstance(self.query_payload['aggregate'], list):
                        self.query_payload['aggregate'].append(aggregate)
                    else:
                        self.query_payload['aggregate'] = list(self.query_payload.get('aggregate'))
                        self.query_payload['aggregate'].append(aggregate)
                else:
                    self.query_payload.update({"aggregate": aggregate})
        return self

    def HAVING(self):
        # TODO: To be implemented
        return self

    def LIMIT(self, arg):
        assert isinstance(arg, PayloadBuilder.SCHEMA_TYPE_MAP[PayloadBuilder.find_type('limit')[0]])
        self.query_payload.update({"limit": arg})
        return self

    def ORDER_BY(self, *args):
        for arg in args:
            sort = {}
            if self.verify_orderby(arg):
                sort.update({"column": arg[0], "direction": arg[1]})
                if 'sort' in self.query_payload:
                    if isinstance(self.query_payload['sort'], list):
                        self.query_payload['sort'].append(sort)
                    else:
                        self.query_payload['sort'] = list(self.query_payload.get('sort'))
                        self.query_payload['sort'].append(sort)
                else:
                    self.query_payload.update({"sort": sort})
        return self

    def payload(self):
        return json.dumps(self.query_payload)

    def query_params(self):
        where = self.query_payload['where']
        query_params = {where['column']: where['value']}
        for key, value in where.items():
            if key == 'and':
                query_params.update({value['column']: value['value']})
        return urllib.parse.urlencode(query_params)

if __name__ == "__main__":
    pb = PayloadBuilder()
    # Select
    sql = pb.\
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

    pb = PayloadBuilder()
    # Insert
    sql = pb.\
        INSERT_INTO('schedules').\
        INSERT(id='test', process_name='sleep', type=3, repeat=45677).\
        payload()
    print(sql)

    pb = PayloadBuilder()
    # Update
    sql = pb.\
        UPDATE_TABLE('schedules').\
        UPDATE(id='test', process_name='sleep', type=3, repeat=45677).\
        WHERE(['id', '=', 'test']). \
        payload()
    print(sql)

    from foglamp.core.service_registry.service_registry import Service
    from foglamp.storage.storage import Storage

    Service.Instances.register(name="store", s_type="Storage", address="0.0.0.0", port=8080)

    pb = PayloadBuilder()
    sql = pb.WHERE(["key", "=", "CoAP"]).payload()
    tbl_name = 'configuration'
    q = sql
    print(sql)
    print(Storage().query_tbl_with_payload(tbl_name, q))

    pb = PayloadBuilder()
    # sql = pb.WHERE(["key", "=", "COAP_CONF"]).AND_WHERE(["ts", "=", "2017-09-15 12:33:22.619847+05:30"]).query_params()
    sql = pb.WHERE(["key", "=", "CoAP"]).query_params()
    print(sql)
    tbl_name = 'configuration'
    print(Storage().query_tbl(tbl_name, sql))

    print(PayloadBuilder.find_type('where_column')[0])
