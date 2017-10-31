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
import numbers

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
            if len(arg) == 1:
                arg.append('asc')

            if len(arg) == 2:
                if arg[1].upper() in ['ASC', 'DESC']:
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
    def ALIAS(cls, *args):
        raise NotImplementedError("To be implemented")

    @classmethod
    def SELECT(cls, *args):
        for arg in args:
            if cls.verify_select(arg):
                if 'return' not in cls.query_payload:
                    cls.query_payload["return"] = list()
                if isinstance(arg, tuple):
                    for a in arg:
                        select = json.loads(a) if cls.is_json(a) else a
                        cls.query_payload["return"].append(select)
                else:
                    select = json.loads(arg) if cls.is_json(arg) else arg
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
        cls.query_payload["group"] = ', '.join(args)
        return cls

    @classmethod
    def AGGREGATE(cls, arg, *args):
        # Pass multiple arguments in a single tuple also. Useful when called from external process i.e. api, test.
        args = (arg,) + args if not isinstance(arg, tuple) else arg
        for arg in args:
            aggregate = OrderedDict()
            if cls.verify_aggregation(arg):
                aggregate["operation"] = arg[0]
                aggregate["column"] = arg[1]
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
