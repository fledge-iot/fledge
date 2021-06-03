# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Storage layer python client payload builder
"""

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

from collections import OrderedDict
import json
import urllib.parse
import numbers

from fledge.common import logger


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

    def __init__(self, initial_payload=OrderedDict()):
        # TODO: Investigate why simple "self.__class__.query_payload = initial_payload" is not working
        self.__class__.query_payload = initial_payload if len(initial_payload) else OrderedDict()

    @staticmethod
    def verify_select(arg):
        retval = False
        if isinstance(arg, str):
            retval = True
        elif isinstance(arg, tuple):
            retval = True
        return retval

    @staticmethod
    def verify_condition(arg):
        retval = False
        if isinstance(arg, list):
            if len(arg) == 3:
                if arg[1] in ['like', '<', '>', '=', '>=', '<=', '!=', 'newer', 'older', 'in', 'not in']:
                    retval = True
                if arg[1] in ['in', 'not in']:
                    if isinstance(arg[2], list):
                        retval = True
        return retval

    @staticmethod
    def verify_aggregation(arg):
        retval = False
        if isinstance(arg, list):
            if len(arg) == 1 and arg[0] == "all":
                retval = True
            elif len(arg) == 2:
                if arg[0] in ['min', 'max', 'avg', 'sum', 'count']:
                    retval = True
        return retval

    @staticmethod
    def verify_orderby(arg):
        retval = False
        if isinstance(arg, list):
            if len(arg) == 1:
                arg.append('asc')

            if len(arg) == 2:
                if arg[1].upper() in ['ASC', 'DESC']:
                    retval = True
        return retval

    @staticmethod
    def verify_alias(arg):
        retval = False
        if isinstance(arg, tuple):
            if len(arg) == 2:
                retval = True
            if len(arg) == 3:
                if arg[1] in ['min', 'max', 'avg', 'sum', 'count']:
                    retval = True
        return retval

    @staticmethod
    def verify_json_property(arg):
        retval = False
        if isinstance(arg, tuple):
            if len(arg) == 3:
                if isinstance(arg[1], list):
                    retval = True
        return retval

    @staticmethod
    def is_json(myjson):
        try:
            json_object = json.loads(myjson)
        except (ValueError, Exception):
            return False
        return True

    @classmethod
    def add_clause_to_select(cls, clause, qp_list, col, clause_value):
        for i, item in enumerate(qp_list):
            if isinstance(item, str):
                if item == col:
                    with_clause = OrderedDict()
                    with_clause['column'] = item
                    with_clause[clause] = clause_value
                    qp_list[i] = with_clause
            if isinstance(item, dict):
                if 'json' in qp_list[i] and qp_list[i]['json']['column'] == col:
                    qp_list[i][clause] = clause_value
                elif 'column' in qp_list[i] and qp_list[i]['column'] == col:
                    qp_list[i][clause] = clause_value

    @classmethod
    def add_clause_to_aggregate(cls, clause, qp_list, col, opr, clause_value):
        if isinstance(qp_list, dict):
            if 'json' in qp_list:
                if qp_list['json']['column'] == col and qp_list['operation'] == opr:
                    qp_list[clause] = clause_value
            elif qp_list['column'] == col and qp_list['operation'] == opr:
                qp_list[clause] = clause_value

        if isinstance(qp_list, list):
            for i, item in enumerate(qp_list):
                if isinstance(item, dict):
                    if 'json' in qp_list[i]:
                        if qp_list[i]['json']['column'] == col and qp_list[i]['operation'] == opr:
                            qp_list[i][clause] = clause_value
                    elif qp_list[i]['column'] == col and qp_list[i]['operation'] == opr:
                        qp_list[i][clause] = clause_value

    @classmethod
    def add_clause_to_group(cls, clause, qp, col, clause_value):
        item = qp['group']
        if cls.is_json(item) is False and isinstance(item, str):
            if item == col:
                with_clause = OrderedDict()
                with_clause['column'] = item
                with_clause[clause] = clause_value
                qp['group'] = with_clause
        if isinstance(item, dict) or cls.is_json(item) is True:
            my_item = json.loads(item) if isinstance(item, dict) is False else item
            if 'column' in my_item and my_item['column'] == col:
                my_item[clause] = clause_value
            qp['group'] = my_item

    @classmethod
    def _add_clause(cls, clause, main_key, args):
        """
        Adds "alias" and "format" clauses to columns in payload info. Currently, adding clauses is supported at two
        actions only - SELECT and AGGREGATE.

        :param clause: either "alias" or "format"
        :param main_key: either "return" or "aggregate"
        :param args: each arg is a tuple. The len of tuple depends upon main_key. If main_key is "return" i.e. SELECT,
                     then each tuple will contain (col, alias). If main_key is "aggregate", then each tuple will contain
                     (col, operation, alias) because col can be repeated in aggregate with different "operations".
        :return:
        """
        if clause not in ['alias', 'format', 'group']:
            return cls

        if main_key in ['return', 'aggregate', 'group']:
            for arg in args:
                if cls.verify_alias(arg):
                    if main_key == 'return':
                        col = arg[0]
                        alias = arg[1]
                        cls.add_clause_to_select(clause, cls.query_payload[main_key], col, alias)
                    if main_key == 'aggregate':
                        col = arg[0]
                        opr = arg[1]
                        alias = arg[2]
                        cls.add_clause_to_aggregate(clause, cls.query_payload[main_key], col, opr, alias)
                    if main_key == 'group':
                        col = arg[0]
                        alias = arg[1]
                        cls.add_clause_to_group(clause, cls.query_payload, col, alias)

        return cls

    @classmethod
    def ALIAS(cls, main_key, *args):
        """
        Adds "alias" to columns in payload info. Currently, adding clauses is supported at two
        actions only - SELECT and AGGREGATE.

        :param main_key: either "return" or "aggregate" or "group"
        :param args: each arg is a tuple. The len of tuple depends upon main_key. If main_key is "return" i.e. SELECT,
                     then each tuple will contain (col, alias). If main_key is "aggregate", then each tuple will contain
                     (col, operation, alias) because col can be repeated in aggregate with different "operations".
        :return:
        :example:
        PayloadBuilder().SELECT(("name", "id")).ALIAS('return', ('name', 'my_name'), ('id', 'my_id')).payload() returns
            {"return": [{"column": "name", "alias": "my_name"},
                        {"column": "id", "alias": "my_id"}]}

        PayloadBuilder().SELECT(("name", ["id", "reason"]).ALIAS('return', ('name', 'my_name'), ('id', 'my_id')).payload() returns
            {"return": [{"alias": "my_name", "column": "name"},
                        {
                              "json" : {
                                          "column"     : "id",
                                          "properties" : "reason"
                                       },
                              "alias" : "my_id"
                        }
                       ]
            }

        PayloadBuilder().AGGREGATE((["min", "values"], ["max", "values"], ["avg", "values"])).ALIAS('aggregate',
                                                           ('values', 'min', 'min_values'),
                                                           ('values', 'max', 'max_values'),
                                                           ('values', 'avg', 'avg_values')).payload() returns
            {"aggregate": [{"operation": "min", "column": "values", "alias": "min_values"},
                           {"operation": "max", "column": "values", "alias": "max_values"},
                           {"operation": "avg", "column": "values", "alias": "avg_values"}]}

        PayloadBuilder().AGGREGATE((["min", ["values", "rate"]], ["max", ["values", "rate"]], ["avg", ["values", "rate"]])).\
        ALIAS('aggregate', ('values', 'min', 'Minimum'), ('values', 'max', 'Maximum'), ('values', 'avg', 'Average')).payload() returns
            {
              "aggregate": [
                {
                  "operation": "min",
                  "json"      : {
                                    "column"     : "values",
                                    "properties" : "rate"
                                },
                  "alias": "Minimum"
                },
                {
                  "operation": "max",
                  "json"      : {
                                    "column"     : "values",
                                    "properties" : "rate"
                                },
                  "alias": "Maximum"
                },
                {
                  "operation": "avg",
                  "json"      : {
                                    "column"     : "values",
                                    "properties" : "rate"
                                },
                  "alias": "Average"
                }
              ]
            }
        """
        return cls._add_clause('alias', main_key, args)

    @classmethod
    def FORMAT(cls, main_key, *args):
        """
        Adds "format" to columns in payload info. Currently, adding clauses is supported at two
        actions only - SELECT and AGGREGATE.

        :param main_key: either "return" or "aggregate"
        :param args: each arg is a tuple. The len of tuple depends upon main_key. If main_key is "return" i.e. SELECT,
                     then each tuple will contain (col, format). If main_key is "aggregate", then each tuple will contain
                     (col, operation, format) because col can be repeated in aggregate with different "operations".
        :return:
        :example:
        PayloadBuilder().SELECT(("reading", "user_ts")).ALIAS('return', ('user_ts', 'timestamp')).\
            FORMAT('return', ('user_ts', "YYYY-MM-DD HH24:MI:SS.MS")).payload() returns
            {"return": ["reading", {"format": "YYYY-MM-DD HH24:MI:SS.MS", "column": "user_ts", "alias": "timestamp"}]}
        """
        return cls._add_clause('format', main_key, args)

    @classmethod
    def SELECT(cls, *args):
        """
        Forms a json to return a list of columns.

        :param args: list of args. Can be a single str, a single list for a json col, a tuple of str and/or json cols
        :return:
        """
        for arg in args:
            if cls.verify_select(arg):
                if 'return' not in cls.query_payload:
                    cls.query_payload["return"] = list()
                if isinstance(arg, tuple):
                    for a in arg:
                        if isinstance(a, list):
                            select = {"json": {'column': a[0], 'properties': a[1]}}
                        elif isinstance(a, str):
                            select = json.loads(a) if cls.is_json(a) else a
                        else:
                            continue
                        cls.query_payload["return"].append(select)
                else:
                    if isinstance(arg, list):
                        select = {"json": {'column': arg[0], 'properties': arg[1]}}
                    elif isinstance(arg, str):
                        select = json.loads(arg) if cls.is_json(arg) else arg
                    else:
                        continue
                    cls.query_payload["return"].append(select)
        return cls

    @classmethod
    def FROM(cls, tbl_name):
        cls.query_payload["table"] = tbl_name
        return cls

    @classmethod
    def DISTINCT(cls, cols):
        if cols is None:
            return cls
        if not isinstance(cols, list):
            return cls
        if len(cols) == 0:
            return cls
        cls.query_payload["modifier"] = "distinct"
        cls.query_payload["return"] = cols
        return cls

    @classmethod
    def UPDATE_TABLE(cls, tbl_name):
        return cls.FROM(tbl_name)

    @classmethod
    def COLS(cls, kwargs):
        values = OrderedDict()
        for key, value in kwargs.items():
            values[key] = value
        return values

    @classmethod
    def SET(cls, **kwargs):
        if 'values' in cls.query_payload:
            cls.query_payload["values"].update(cls.COLS(kwargs))
        else:
            cls.query_payload["values"] = cls.COLS(kwargs)
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
    def add_new_clause(cls, and_or, main, new):
        """
        Recursively searches for the innermost and/or block, or cls.query_payload["where"] if none, in "main" to add
        the 'new' condition block under "and_or" key.

        Args:
            and_or: one of 'and', 'or'
            main: Dict (cls.query_payload["where"] or the innermost and/or subset of it) where
                  the new condition block is to be added
            new: condition block to be added

        Returns:
        """
        if 'and' not in main:
            if 'or' not in main:
                main[and_or] = new
            else:
                cls.add_new_clause(and_or, main['or'], new)
        else:
            cls.add_new_clause(and_or, main['and'], new)

    @classmethod
    def WHERE(cls, arg, *args):
        # Pass multiple arguments in a single tuple also. Useful when called from external process i.e. api, test.
        args = (arg,) + args if not isinstance(arg, tuple) else arg
        for arg in args:
            condition = OrderedDict()
            if cls.verify_condition(arg):
                condition["column"] = arg[0]
                condition["condition"] = arg[1]
                condition["value"] = arg[2]
                if 'where' not in cls.query_payload:
                    cls.query_payload["where"] = condition
                else:
                    cls.add_new_clause('and', cls.query_payload['where'], condition)
        return cls

    @classmethod
    def AND_WHERE(cls, arg, *args):
        # Pass multiple arguments in a single tuple also. Useful when called from external process i.e. api, test.
        args = (arg,) + args if not isinstance(arg, tuple) else arg
        for arg in args:
            condition = OrderedDict()
            if cls.verify_condition(arg):
                condition["column"] = arg[0]
                condition["condition"] = arg[1]
                condition["value"] = arg[2]
                if 'where' not in cls.query_payload:
                    cls.query_payload["where"] = condition
                else:
                    cls.add_new_clause('and', cls.query_payload['where'], condition)
        return cls

    @classmethod
    def OR_WHERE(cls, arg, *args):
        # Pass multiple arguments in a single tuple also. Useful when called from external process i.e. api, test.
        args = (arg,) + args if not isinstance(arg, tuple) else arg
        for arg in args:
            condition = OrderedDict()
            if cls.verify_condition(arg):
                condition["column"] = arg[0]
                condition["condition"] = arg[1]
                condition["value"] = arg[2]
                if 'where' not in cls.query_payload:
                    cls.query_payload["where"] = condition
                else:
                    cls.add_new_clause('or', cls.query_payload['where'], condition)
        return cls

    @classmethod
    def GROUP_BY(cls, *args):
        # TODO: Add dict format for args
        cls.query_payload["group"] = ', '.join(args)
        return cls

    @classmethod
    def AGGREGATE(cls, arg, *args):
        """
        Forms a json to return a dict (for a single col) or a list of dicts required in an aggregate clause.

        :param args: Can be a single list or a tuple of lists. The list is given in structure [opr, col].
                     col can be a str or another list for json col. For json col, the structure is [col, properties].
        :return:
        :example:
        PayloadBuilder().AGGREGATE((["min", "values"], ["max", "values"], ["avg", "values"])).ALIAS('aggregate',
                                                           ('values', 'min', 'min_values'),
                                                           ('values', 'max', 'max_values'),
                                                           ('values', 'avg', 'avg_values')).payload() returns
            {"aggregate": [{"operation": "min", "column": "values", "alias": "min_values"},
                           {"operation": "max", "column": "values", "alias": "max_values"},
                           {"operation": "avg", "column": "values", "alias": "avg_values"}]}

        PayloadBuilder().AGGREGATE(["all"])
        """

        # Pass multiple arguments in a single tuple also. Useful when called from external process i.e. api, test.
        args = (arg,) + args if not isinstance(arg, tuple) else arg
        for arg in args:
            aggregate = OrderedDict()
            if cls.verify_aggregation(arg):
                aggregate["operation"] = arg[0]
                if len(arg) >= 2:
                    if isinstance(arg[1], list):
                        aggregate["json"] = {'column': arg[1][0], 'properties': arg[1][1]}
                    elif isinstance(arg[1], str):
                        aggregate["column"] = arg[1]
                    else:
                        continue
                if 'aggregate' in cls.query_payload:
                    if not isinstance(cls.query_payload['aggregate'], list):
                        cls.query_payload['aggregate'] = [cls.query_payload.get('aggregate')]
                    cls.query_payload['aggregate'].append(aggregate)
                else:
                    cls.query_payload["aggregate"] = aggregate
        return cls

    @classmethod
    def HAVING(cls):
        raise NotImplementedError("To be implemented")

    @classmethod
    def LIMIT(cls, arg):
        if isinstance(arg, numbers.Real):
            cls.query_payload["limit"] = arg
        return cls

    @classmethod
    def OFFSET(cls, arg):
        if isinstance(arg, numbers.Real):
            cls.query_payload["skip"] = arg
        return cls

    SKIP = OFFSET

    @classmethod
    def ORDER_BY(cls, arg, *args):
        # Pass multiple arguments in a single tuple also. Useful when called from external process i.e. api, test.
        args = (arg,) + args if not isinstance(arg, tuple) else arg
        for arg in args:
            sort = OrderedDict()
            if cls.verify_orderby(arg):
                sort["column"] = arg[0]
                sort["direction"] = arg[1]
                if 'sort' in cls.query_payload:
                    if not isinstance(cls.query_payload['sort'], list):
                        cls.query_payload['sort'] = [cls.query_payload.get('sort')]
                    cls.query_payload['sort'].append(sort)
                else:
                    cls.query_payload["sort"] = sort
        return cls

    @classmethod
    def EXPR(cls, arg, *args):
        args = (arg,) + args if not isinstance(arg, tuple) else arg

        for arg in args:
            expr = OrderedDict()
            expr["column"] = arg[0]
            expr["operator"] = arg[1]
            expr["value"] = arg[2]

            if 'expressions' in cls.query_payload:
                cls.query_payload['expressions'].append(expr)
            else:
                cls.query_payload['expressions'] = [expr]
        return cls

    @classmethod
    def JSON_PROPERTY(cls, *args):
        """
        Forms a json to return a list of dicts required in a json_properties clause.

        :param args: Can be a single tuple or a sequence of tuples. Each tuple is given in structure [col, path, value].
                     col and value should be a str and path should be a list.
        :return:
        :example:
        PayloadBuilder().JSON_PROPERTY(("data", [ "url", "value" ], "new value")).payload() returns
            {
                "json_properties" : [
                            {
                                "column" : "data",
                                "path"   : [ "url", "value" ],
                                "value"  : "new value"
                            }
                            ]
            }
        """

        # Pass multiple arguments in a single tuple also. Useful when called from external process i.e. api, test.
        for arg in args:
            json_property = OrderedDict()
            if cls.verify_json_property(arg):
                json_property["column"] = arg[0]
                json_property["path"] = arg[1]
                json_property["value"] = arg[2]
                if 'json_properties' in cls.query_payload:
                    if not isinstance(cls.query_payload['json_properties'], list):
                        cls.query_payload['json_properties'] = [cls.query_payload.get('json_properties')]
                    cls.query_payload['json_properties'].append(json_property)
                else:
                    cls.query_payload["json_properties"] = [json_property]
        return cls

    @classmethod
    def TIMEBUCKET(cls, timestamp, size="1", fmt=None, alias=None):
        """
        Forms a json to return a dict of timebucket col

        :param timestamp: timestamp col
        :param size: bucket size in seconds, defaults to "1"
        :param fmt: format string, optional
        :param alias: alias, optional
        :return:
        :example:
        PayloadBuilder().TIMEBUCKET("user_ts", "5").payload() returns
            "timebucket" :  {
                               "timestamp" : "user_ts",
                               "size"      : "5"
                        }

        PayloadBuilder().TIMEBUCKET("user_ts", "5", format="DD-MM-YYYYY HH24:MI:SS").payload() returns
            "timebucket" :  {
                               "timestamp" : "user_ts",
                               "size"      : "5",
                               "format"    : "DD-MM-YYYYY HH24:MI:SS"
                        }

        PayloadBuilder().TIMEBUCKET("user_ts", "5", format="DD-MM-YYYYY HH24:MI:SS", alias="bucket").payload() returns
            "timebucket" :  {
                               "timestamp" : "user_ts",
                               "size"      : "5",
                               "format"    : "DD-MM-YYYYY HH24:MI:SS",
                               "alias"     : "bucket"
                        }
        """

        timebucket = OrderedDict()
        timebucket["timestamp"] = timestamp
        timebucket["size"] = size
        if fmt is not None:
            timebucket["format"] = fmt
        if alias is not None:
            timebucket["alias"] = alias
        cls.query_payload["timebucket"] = timebucket

        return cls

    @classmethod
    def payload(cls):
        return json.dumps(cls.query_payload, sort_keys=False)

    @classmethod
    def chain_payload(cls):
        """
        Sometimes, we may want to create payload incremently, based upon some conditions, this method will come
        handy in such Use cases.
        """
        return cls.query_payload

    @classmethod
    def query_params(cls):
        where = cls.query_payload['where']
        query_params = OrderedDict({where['column']: where['value']})
        for key, value in where.items():
            if key == 'and':
                query_params.update({value['column']: value['value']})
        return urllib.parse.urlencode(query_params)
