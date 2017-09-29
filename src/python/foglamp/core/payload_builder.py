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

import json
from collections import OrderedDict
from foglamp import logger

_LOGGER = logger.setup(__name__)


class Schema(object):

    scheduled_processes = {
        'name': 'name',
        'process': 'process'
    }

    schedules = {
        'id': 'id',
        'process_name': 'process_name',
        'schedule_name': 'schedule_name',
        'schedule_type': 'schedule_type',
        'schedule_interval': 'schedule_interval',
        'schedule_time': 'schedule_time',
        'schedule_day': 'schedule_day'
    }

    tasks = {
        'id': 'id',
        'process_name': 'process_name',
        'state': 'state',
        'start_time': 'start_time',
        'end_time': 'end_time',
        'reason': 'reason',
        'pid': 'pid',
        'exit_code': 'exit_code'
    }

class PayloadBuilder(object):
    """ Payload Builder to be used in Python wrapper class for Storage Service
    Ref: https://docs.google.com/document/d/1qGIswveF9p2MmAOw_W1oXpo_aFUJd3bXBkW563E16g0/edit#
    Ref: http://json-schema.org/
    """

    def __init__(self, payload=OrderedDict()):
        self.payload = payload

    @staticmethod
    def verify_condition(arg):
        retval = False
        if isinstance(arg, list):
            if len(arg) == 3:
                if arg[1] in ['<', '>', '=', '>=', '<=', 'LIKE', 'IN', '!=']:
                    retval = True
        return retval

    @staticmethod
    def verify_aggregation(arg):
        retval = False
        if isinstance(arg, list):
            if len(arg) == 2:
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

    def SELECT(self, *args):
        if len(args) > 0:
            self.payload.update({"columns": ','.join(args)})
        return self

    def SELECTALL(self, *args):
        return self

    def FROM(self, tbl_name):
        self.payload.update({'table': tbl_name})
        return self

    def UPDATETABLE(self, tbl_name):
        return self.FROM(tbl_name)

    def COLS(self, kwargs):
        values = {}
        for key, value in kwargs.items():
            values.update({key: value})
        return values

    def UPDATE(self, **kwargs):
        self.payload.update({'values': self.COLS(kwargs)})
        return self

    def INSERT(self, **kwargs):
        self.payload.update(self.COLS(kwargs))
        return self

    def INSERTINTO(self, tbl_name):
        return self.FROM(tbl_name)

    def DELETE(self, tbl_name):
        return self.FROM(tbl_name)

    def WHERE(self, arg):
        condition = {}
        if self.verify_condition(arg):
            condition.update({'column': arg[0], 'condition': arg[1], 'value': arg[2]})
            self.payload.update({'where': condition})
        return self

    def WHERE_AND(self, *args):
        for arg in args:
            condition = {}
            if self.verify_condition(arg):
                condition.update({'column': arg[0], 'condition': arg[1], 'value': arg[2]})
                self.payload['where'].update({'and': condition})
        return self

    def WHERE_OR(self, *args):
        for arg in args:
            if self.verify_condition(arg):
                condition = {}
                condition.update({'column': arg[0], 'condition': arg[1], 'value': arg[2]})
                self.payload['where'].update({'or': condition})
        return self

    def GROUPBY(self, *args):
        self.payload.update({'group': ', '.join(args)})
        return self

    def AGGREGATION(self, *args):
        for arg in args:
            aggregation = {}
            if self.verify_aggregation(arg):
                aggregation.update({'operation': arg[0], 'column': arg[1]})
                if 'aggregation' in self.payload:
                    if isinstance(self.payload['aggregation'], list):
                        self.payload['aggregation'].append(aggregation)
                    else:
                        self.payload['aggregation'] = list(self.payload.get('aggregation'))
                        self.payload['aggregation'].append(aggregation)
                else:
                    self.payload.update({'aggregation': aggregation})
        return self

    def HAVING(self):
        # TODO: To be implemented
        return self

    def LIMIT(self, arg):
        if isinstance(arg, int):
            self.payload.update({'limit': arg})
        return self

    def ORDERBY(self, *args):
        for arg in args:
            sort = {}
            if self.verify_orderby(arg):
                sort.update({'column': arg[0], 'direction': arg[1]})
                if 'sort' in self.payload:
                    if isinstance(self.payload['sort'], list):
                        self.payload['sort'].append(sort)
                    else:
                        self.payload['sort'] = list(self.payload.get('sort'))
                        self.payload['sort'].append(sort)
                else:
                    self.payload.update({'sort': sort})
        return self

    def execute(self):
        return str(self.payload)

if __name__ == '__main__':
    pb = PayloadBuilder(payload=dict())
    # Select
    sql = pb.\
        SELECT('id', 'type', 'repeat', 'process_name').\
        FROM('schedules').\
        WHERE(['id', '=', 'test']).\
        WHERE_AND(['process_name', '=', 'test']). \
        WHERE_OR(['process_name', '=', 'sleep']).\
        LIMIT(3).\
        GROUPBY('process_name', 'id').\
        ORDERBY(['process_name', 'desc']).\
        AGGREGATION(['count', 'process_name']).\
        execute()
    print(sql)

    pb = PayloadBuilder(payload=dict())
    # Insert
    sql = pb.\
        INSERTINTO('schedules').\
        INSERT(id='test', process_name='sleep', type=3, repeat=45677).\
        execute()
    print(sql)

    pb = PayloadBuilder(payload=dict())
    # Insert
    sql = pb.\
        UPDATETABLE('schedules').\
        UPDATE(id='test', process_name='sleep', type=3, repeat=45677).\
        WHERE(['id', '=', 'test']). \
        execute()
    print(sql)

    from foglamp.storage.storage import Storage

    pb = PayloadBuilder(payload=dict())
    sql = pb.SELECTALL().FROM('scheduled_processes').execute()

    print(Storage.query_tbl(sql['table']))
