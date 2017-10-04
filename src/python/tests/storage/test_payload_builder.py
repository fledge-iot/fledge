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


class TestPayloadBuilder:

    @pytest.mark.parametrize("test_input, expected", [
        ("name", {"columns": "name"}),
        ("name,id", {"columns": "name,id"})
    ])
    def test_select_payload(self, test_input, expected):
        pb = PayloadBuilder()
        res = pb.SELECT(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        ("test", {"table": "test"}),
        ("test, test2", {"table": "test, test2"})
    ])
    def test_from_payload(self, test_input, expected):
        pb = PayloadBuilder()
        res = pb.FROM(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (['name', '=', 'test'], {'where': {'column': 'name', 'condition': '=', 'value': 'test'}})
    ])
    def test_where_payload(self, test_input, expected):
        pb = PayloadBuilder()
        res = pb.WHERE(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (3, {'limit': 3}),
        (3.5, {}),
        ('invalid', {})
    ])
    def test_limit_payload(self, test_input, expected):
        pb = PayloadBuilder()
        res = pb.LIMIT(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        (['name', 'asc'], {'sort': {'column': 'name', 'direction': 'asc'}}),
        (['name', 'desc'], {'sort': {'column': 'name', 'direction': 'desc'}}),
        (['name'], {'sort': {'column': 'name', 'direction': 'asc'}}),
        (['name', 'invalid'], {})
    ])
    def test_order_by_payload(self, test_input, expected):
        pb = PayloadBuilder()
        res = pb.ORDER_BY(test_input).payload()
        assert expected == json.loads(res)

    @pytest.mark.parametrize("test_input, expected", [
        ("name", {'group': 'name'}),
        ("name,id", {'group': 'name,id'})
    ])
    def test_group_by_payload(self, test_input, expected):
        pb = PayloadBuilder()
        res = pb.GROUP_BY(test_input).payload()
        assert expected == json.loads(res)
