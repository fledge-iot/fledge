# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END
import pytest
import json
import os
import py
from foglamp.storage.payload_builder import PayloadBuilder

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def _payload(test_data_file=None):
    _dir = os.path.dirname(os.path.realpath(__file__))
    file_path = py.path.local(_dir).join('/').join(test_data_file)

    with open(str(file_path)) as data_file:
        json_data = json.load(data_file)
    return json_data


@pytest.allure.feature("unit")
@pytest.allure.story("payload_builder")
class TestPayloadBuilderRead:
    """
    This class tests all SELECT (Read) data specific payload methods of payload builder
    """

    @pytest.mark.parametrize("test_input, expected", [
        ("name", _payload("data/payload_select1.json")),
        (("name", "id"), _payload("data/payload_select2.json"))
    ])
    def test_select_payload(self, test_input, expected):
        res = PayloadBuilder().SELECT(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        ("test", _payload("data/payload_from1.json")),
        ("test, test2", _payload("data/payload_from2.json"))
    ])
    def test_from_payload(self, test_input, expected):
        res = PayloadBuilder().FROM(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (["name", "=", "test"], _payload("data/payload_conditions1.json")),
        (["id", ">", 1], _payload("data/payload_conditions2.json")),
        (["id", "<", 1.5], _payload("data/payload_conditions3.json")),
        (["id", ">=", 9], _payload("data/payload_conditions4.json")),
        (["id", "<=", 99], _payload("data/payload_conditions5.json")),
        (["id", "!=", "False"], _payload("data/payload_conditions6.json"))

    ])
    def test_conditions_payload(self, test_input, expected):
        res = PayloadBuilder().WHERE(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (["name", "=", "test"], _payload("data/payload_conditions1.json"))
    ])
    def test_where_payload(self, test_input, expected):
        res = PayloadBuilder().WHERE(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input_1, test_input_2, expected", [
        (["name", "=", "test"], ["id", ">", 3], _payload("data/payload_and_where1.json"))
    ])
    def test_and_where_payload(self, test_input_1, test_input_2, expected):
        res = PayloadBuilder().WHERE(test_input_1).AND_WHERE(test_input_2).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input_1, test_input_2, test_input_3, expected", [
        (["name", "=", "test"], ["id", ">", 3], ["value", "!=", 0], _payload("data/payload_and_where2.json"))
    ])
    def test_multiple_and_where_payload(self, test_input_1, test_input_2, test_input_3, expected):
        res = PayloadBuilder().WHERE(test_input_1).AND_WHERE(test_input_2).AND_WHERE(test_input_3).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input_1, test_input_2, expected", [
        (["name", "=", "test"], ["id", ">", 3], _payload("data/payload_or_where1.json"))
    ])
    def test_or_where_payload(self, test_input_1, test_input_2, expected):
        res = PayloadBuilder().WHERE(test_input_1).OR_WHERE(test_input_2).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input_1, test_input_2, test_input_3, expected", [
        (["name", "=", "test"], ["id", ">", 3], ["value", "!=", 0], _payload("data/payload_or_where2.json"))
    ])
    def test_multiple_or_where_payload(self, test_input_1, test_input_2, test_input_3, expected):
        res = PayloadBuilder().WHERE(test_input_1).OR_WHERE(test_input_2).OR_WHERE(test_input_3).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (3, _payload("data/payload_limit1.json")),
        (3.5, _payload("data/payload_limit2.json")),
        ("invalid", {})
    ])
    def test_limit_payload(self, test_input, expected):
        res = PayloadBuilder().LIMIT(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (["name", "asc"], _payload("data/payload_order_by1.json")),
        (["name", "desc"], _payload("data/payload_order_by2.json")),
        ((["name", "desc"], ["id", "asc"], ["ts", "asc"]), _payload("data/payload_order_by3.json")),
        (["name"], _payload("data/payload_order_by1.json")),
        (["name", "invalid"], {})
    ])
    def test_order_by_payload(self, test_input, expected):
        res = PayloadBuilder().ORDER_BY(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        ("name", _payload("data/payload_group_by1.json")),
        ("name,id", _payload("data/payload_group_by2.json"))
    ])
    def test_group_by_payload(self, test_input, expected):
        res = PayloadBuilder().GROUP_BY(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (["min", "values"], _payload("data/payload_aggregate1.json")),
        (["max", "values"], _payload("data/payload_aggregate2.json")),
        (["avg", "values"], _payload("data/payload_aggregate3.json")),
        (["sum", "values"], _payload("data/payload_aggregate4.json")),
        (["count", "values"], _payload("data/payload_aggregate5.json")),
        ((["min", "values"], ["max", "values"], ["avg", "values"]), _payload("data/payload_aggregate6.json")),
        (["invalid", "values"], {})
    ])
    def test_aggregate_payload(self, test_input, expected):
        res = PayloadBuilder().AGGREGATE(test_input).payload()
        assert expected == json.loads(res)

    def test_select_all_payload(self):
        res = PayloadBuilder().SELECT().payload()
        expected = {}
        assert expected == json.loads(res)

    def test_select_distinct_payload(self):
        expr = PayloadBuilder().\
            SELECT().DISTINCT(["description"])\
            .WHERE(["id", "<", 1000]).payload()
        assert _payload("data/payload_distinct.json") == json.loads(expr)

    @pytest.mark.parametrize("test_input, expected", [
        (3, _payload("data/payload_offset1.json")),
        (3.5, _payload("data/payload_offset2.json")),
        ("invalid", {})
    ])
    def test_offset_payload(self, test_input, expected):
        res = PayloadBuilder().OFFSET(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (3, _payload("data/payload_limit_offset1.json")),
        (3.5, _payload("data/payload_limit_offset2.json")),
        ("invalid", {})
    ])
    def test_limit_offset_payload(self, test_input, expected):
        res = PayloadBuilder().LIMIT(test_input).OFFSET(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (3, _payload("data/payload_offset1.json")),
        (3.5, _payload("data/payload_offset2.json")),
        ("invalid", {})
    ])
    def test_skip_payload(self, test_input, expected):
        res = PayloadBuilder().SKIP(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (3, _payload("data/payload_limit_offset1.json")),
        (3.5, _payload("data/payload_limit_offset2.json")),
        ("invalid", {})
    ])
    def test_limit_skip_payload(self, test_input, expected):
        res = PayloadBuilder().LIMIT(test_input).SKIP(test_input).payload()
        assert expected == json.loads(res)

    def test_query_params_payload(self):
        res = PayloadBuilder().WHERE(["key", "=", "value1"]).query_params()
        assert "key=value1" == res

    @pytest.mark.parametrize("test_input1, test_input2, expected", [
        (["key1", "=", "value1"], ["key2", "=", 2],  "key1=value1&key2=2"),
    ])
    def test_and_query_params_payload(self, test_input1, test_input2, expected):
        res = PayloadBuilder().WHERE(test_input1).AND_WHERE(test_input2).query_params()
        assert expected == res

    @pytest.mark.parametrize("test_input1, test_input2, expected", [
        (["key1", "=", "value1"], ["key2", "=", 2],  "key1=value1"),
    ])
    def test_or_query_params_payload(self, test_input1, test_input2, expected):
        """Since URL does not support OR hence only 1 value should be parsed as query parameter"""
        res = PayloadBuilder().WHERE(test_input1).OR_WHERE(test_input2).query_params()
        assert expected == res

    @pytest.mark.skip(reason="No support from storage layer yet")
    def test_having_payload(self, expected):
        res = PayloadBuilder().HAVING().payload()
        assert expected == json.loads(res)

    def test_expr_payload(self):

        res = PayloadBuilder().WHERE(["key", "=", "READINGS"]).EXPR(["value", "+", 10]).payload()
        assert _payload("data/payload_expr1.json") == json.loads(res)

        exprs = (["value1", "+", 10], ["value2", "-", 5])  # a tuple
        res = PayloadBuilder().WHERE(["key", "=", "READINGS"]).EXPR(exprs).payload()
        assert 2 == len(json.loads(res))
        assert _payload("data/payload_expr2.json") == json.loads(res)

    def test_complex_select_payload(self):
        res = PayloadBuilder() \
            .SELECT("id", "name") \
            .WHERE(["id", "=", 1]) \
            .AND_WHERE(["name", "=", "test"]) \
            .OR_WHERE(["name", "=", "test2"]) \
            .LIMIT(5) \
            .OFFSET(1) \
            .GROUP_BY("name", "id") \
            .ORDER_BY(["id", "desc"]) \
            .AGGREGATE(["count", "name"]) \
            .payload()
        assert _payload("data/payload_complex_select1.json") == json.loads(res)

    def test_chain_payload(self):
        res_chain = PayloadBuilder() \
            .SELECT("id", "name") \
            .WHERE(["id", "=", 1]) \
            .AND_WHERE(["name", "=", "test"]) \
            .OR_WHERE(["name", "=", "test2"]) \
            .chain_payload()

        res = PayloadBuilder(res_chain) \
            .LIMIT(5) \
            .OFFSET(1) \
            .GROUP_BY("name", "id") \
            .ORDER_BY(["id", "desc"]) \
            .AGGREGATE(["count", "name"]) \
            .payload()

        assert _payload("data/payload_complex_select1.json") == json.loads(res)


@pytest.allure.feature("unit")
@pytest.allure.story("payload_builder")
class TestPayloadBuilderCreate:
    """
    This class tests all INSERT data specific payload methods of payload builder
    """
    def test_insert_payload(self):
        res = PayloadBuilder().INSERT(key="x").payload()
        assert _payload("data/payload_insert1.json") == json.loads(res)

    def test_insert_into_payload(self):
        res = PayloadBuilder().INSERT_INTO("test").payload()
        assert _payload("data/payload_from1.json") == json.loads(res)


class TestPayloadBuilderUpdate:
    """
    This class tests all UPDATE specific payload methods of payload builder
    """
    @pytest.mark.parametrize("test_input, expected", [
        ("test", _payload("data/payload_from1.json")),
    ])
    def test_update_table_payload(self, test_input, expected):
        res = PayloadBuilder().UPDATE_TABLE(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        ("test_update", _payload("data/payload_set1.json")),
    ])
    def test_set_payload(self, test_input, expected):
        res = PayloadBuilder().SET(value=test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("input_set, input_where, input_table, expected", [
        ("test_update", ["name", "=", "test"], "test_tbl",
         _payload("data/payload_update_set_where1.json")),
    ])
    def test_update_set_where_payload(self, input_set, input_where, input_table, expected):
        res = PayloadBuilder().SET(value=input_set).WHERE(input_where).UPDATE_TABLE(input_table).payload()
        assert expected == json.loads(res)


@pytest.allure.feature("unit")
@pytest.allure.story("payload_builder")
class TestPayloadBuilderDelete:
    """
    This class tests all DELETE specific payload methods of payload builder
    """
    @pytest.mark.parametrize("test_input, expected", [
        ("test", _payload("data/payload_from1.json")),
    ])
    def test_delete_payload(self, test_input, expected):
        res = PayloadBuilder().DELETE(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("input_where, input_table, expected", [
        (["name", "=", "test"], "test_tbl",
         _payload("data/payload_delete_where1.json")),
    ])
    def test_delete_where_payload(self, input_where, input_table, expected):
        res = PayloadBuilder().DELETE(input_table).WHERE(input_where).payload()
        assert expected == json.loads(res)
