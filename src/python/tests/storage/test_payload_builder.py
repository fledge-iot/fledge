# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END
import pytest
import json
from foglamp.storage.payload_builder import PayloadBuilder

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestPayloadBuilderRead:

    @pytest.mark.parametrize("test_input, expected", [
        ("name", {"columns": "name"}),
        ("name,id", {"columns": "name,id"})
    ])
    def test_select_payload(self, test_input, expected):
        res = PayloadBuilder().SELECT(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        ("test", {"table": "test"}),
        ("test, test2", {"table": "test, test2"})
    ])
    def test_from_payload(self, test_input, expected):
        res = PayloadBuilder().FROM(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (['name', '=', 'test'], {'where': {'column': 'name', 'condition': '=', 'value': 'test'}}),
        (['id', '>', 1], {'where': {'column': 'id', 'condition': '>', 'value': 1}}),
        (['id', '<', 1.5], {'where': {'column': 'id', 'condition': '<', 'value': 1.5}}),
        (['id', '>=', 9], {'where': {'column': 'id', 'condition': '>=', 'value': 9}}),
        (['id', '<=', 99], {'where': {'column': 'id', 'condition': '<=', 'value': 99}}),
        (['id', '!=', False], {'where': {'column': 'id', 'condition': '!=', 'value': False}})

    ])
    def test_conditions_payload(self, test_input, expected):
        res = PayloadBuilder().WHERE(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (['name', '=', 'test'], {'where': {'column': 'name', 'condition': '=', 'value': 'test'}})
    ])
    def test_where_payload(self, test_input, expected):
        res = PayloadBuilder().WHERE(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input_1, test_input_2, expected", [
        (['name', '=', 'test'], ['id', '>', 3], {'where': {
            'and': {
                'column': 'id', 'condition': '>', 'value': 3},
            'column': 'name', 'condition': '=', 'value': 'test'}})
    ])
    def test_and_where_payload(self, test_input_1, test_input_2, expected):
        res = PayloadBuilder().WHERE(test_input_1).AND_WHERE(test_input_2).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input_1, test_input_2, expected", [
        (['name', '=', 'test'], ['id', '>', 3], {'where': {
            'or': {
                'column': 'id', 'condition': '>', 'value': 3},
            'column': 'name', 'condition': '=', 'value': 'test'}})
    ])
    def test_or_where_payload(self, test_input_1, test_input_2, expected):
        res = PayloadBuilder().WHERE(test_input_1).OR_WHERE(test_input_2).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (3, {'limit': 3}),
        pytest.param(3.5, {'limit': 3.5}, marks=pytest.mark.xfail(reason="FOGL-607 #1")),
        ('invalid', {})
    ])
    def test_limit_payload(self, test_input, expected):
        res = PayloadBuilder().LIMIT(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (['name', 'asc'], {'sort': {'column': 'name', 'direction': 'asc'}}),
        (['name', 'desc'], {'sort': {'column': 'name', 'direction': 'desc'}}),
        pytest.param(['name'], {'sort': {'column': 'name', 'direction': 'asc'}}, marks=pytest.mark.xfail(reason="FOGL-607 #2")),
        (['name', 'invalid'], {})
    ])
    def test_order_by_payload(self, test_input, expected):
        res = PayloadBuilder().ORDER_BY(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        ("name", {'group': 'name'}),
        ("name,id", {'group': 'name,id'})
    ])
    def test_group_by_payload(self, test_input, expected):
        res = PayloadBuilder().GROUP_BY(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (['min', 'values'], {'aggregate': {'column': 'values', 'operation': 'min'}}),
        (['max', 'values'], {'aggregate': {'column': 'values', 'operation': 'max'}}),
        (['avg', 'values'], {'aggregate': {'column': 'values', 'operation': 'avg'}}),
        (['sum', 'values'], {'aggregate': {'column': 'values', 'operation': 'sum'}}),
        (['count', 'values'], {'aggregate': {'column': 'values', 'operation': 'count'}}),
        (['invalid', 'values'], {})
    ])
    def test_aggregate_payload(self, test_input, expected):
        res = PayloadBuilder().AGGREGATE(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        pytest.param('', {"columns": "*"}, marks=pytest.mark.xfail(reason="FOGL-607 #3"))
    ])
    def test_select_all_payload(self, test_input, expected):
        res = PayloadBuilder().SELECT_ALL().payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        pytest.param(3, {'skip': 3}, marks=pytest.mark.xfail(reason="FOGL-607 #1 #4")),
        pytest.param(3.5, {'skip': 3.5}, marks=pytest.mark.xfail(reason="FOGL-607 #1 #4")),
        ('invalid', {})
    ])
    def test_offset_payload(self, test_input, expected):
        res = PayloadBuilder().OFFSET(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (3, {'limit': 3, 'skip': 3}),
        pytest.param(3.5, {'limit': 3.5, 'skip': 3.5}, marks=pytest.mark.xfail(reason="FOGL-607 #1")),
        ('invalid', {})
    ])
    def test_limit_offset_payload(self, test_input, expected):
        res = PayloadBuilder().LIMIT(test_input).OFFSET(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        pytest.param(3, {'skip': 3}, marks=pytest.mark.xfail(reason="FOGL-607 #1 #4")),
        pytest.param(3.5, {'skip': 3.5}, marks=pytest.mark.xfail(reason="FOGL-607 #1 #4")),
        ('invalid', {})
    ])
    def test_skip_payload(self, test_input, expected):
        res = PayloadBuilder().SKIP(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.skip(reason="FOGL-607 #5")
    def test_having_payload(self, test_input, expected):
        res = PayloadBuilder().HAVING().payload()
        assert expected == json.loads(res)

    def test_complex_select_payload(self):
        res = PayloadBuilder() \
            .SELECT('id', 'name') \
            .FROM('table') \
            .WHERE(['id', '=', 1]) \
            .AND_WHERE(['name', '=', 'test']) \
            .OR_WHERE(['name', '=', 'test2']) \
            .LIMIT(1) \
            .GROUP_BY('name', 'id') \
            .ORDER_BY(['id', 'desc']) \
            .AGGREGATE(['count', 'name']) \
            .payload()
        assert {"aggregate":
                          {"column": "name", "operation": "count"},
                      "columns": "id,name", "group": "name, id", "limit": 1,
                      "sort": {"column": "id", "direction": "desc"},
                      "table": "table",
                      "where":
                          {"and": {"column": "name", "condition": "=", "value": "test"},
                           "column": "id", "condition": "=", "or": {
                              "column": "name", "condition": "=", "value": "test2"},
                           "value": 1}} == json.loads(res)


class TestPayloadBuilderCreate:
    def test_insert_payload(self):
        res = PayloadBuilder().INSERT(key='x').payload()
        assert {'key': 'x'} == json.loads(res)

    def test_insert_into_payload(self):
        res = PayloadBuilder().INSERT_INTO('test').payload()
        assert {'table': 'test'} == json.loads(res)


class TestPayloadBuilderUpdate:
    @pytest.mark.parametrize("test_input, expected", [
        ('test', {'table': 'test'}),
    ])
    def test_update_table_payload(self, test_input, expected):
        res = PayloadBuilder().UPDATE_TABLE(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        ('test_update', {"values": {"value": 'test_update'}}),
    ])
    def test_set_payload(self, test_input, expected):
        res = PayloadBuilder().SET(value=test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("input_set, input_where, input_table, expected", [
        ('test_update', ['name', '=', 'test'], 'test_tbl',
         {"table": "test_tbl", "values": {"value": "test_update"},
          "where": {"column": "name", "condition": "=", "value": "test"}}),
    ])
    def test_update_set_where_payload(self, input_set, input_where, input_table, expected):
        res = PayloadBuilder().SET(value=input_set).WHERE(input_where).UPDATE_TABLE(input_table).payload()
        assert expected == json.loads(res)


class TestPayloadBuilderDelete:
    @pytest.mark.parametrize("test_input, expected", [
        ('test', {'table': 'test'}),
    ])
    def test_delete_payload(self, test_input, expected):
        res = PayloadBuilder().DELETE(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("input_where, input_table, expected", [
        (['name', '=', 'test'], 'test_tbl',
         {"table": "test_tbl", "where": {"column": "name", "condition": "=", "value": "test"}}),
    ])
    def test_delete_where_payload(self, input_where, input_table, expected):
        res = PayloadBuilder().DELETE(input_table).WHERE(input_where).payload()
        assert expected == json.loads(res)
