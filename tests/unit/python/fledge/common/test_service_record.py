# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END


""" Test fledge/common/service_record.py """

import pytest

from fledge.common.service_record import ServiceRecord

__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestServiceRecord:

    def test_slots(self):
        slots = ServiceRecord.__slots__
        assert 9 == len(slots)
        assert ['_id', '_name', '_type', '_protocol', '_address', '_port', '_management_port', '_status', '_debug'
                ] == slots

    @pytest.mark.parametrize("name, value", [
        ('Storage', 1), ('Core', 2), ('Southbound', 3), ('Notification', 4), ('Management', 5), ('Northbound', 6),
        ('Dispatcher', 7), ('BucketStorage', 8), ('Pipeline', 9)
    ])
    def test_types(self, name, value):
        assert 9 == len(ServiceRecord.Type)
        assert name == ServiceRecord.Type(value).name

    @pytest.mark.parametrize("name, value", [
        ('Running', 1), ('Shutdown', 2), ('Failed', 3), ('Unresponsive', 4), ('Restart', 5)
    ])
    def test_status(self, name, value):
        assert 5 == len(ServiceRecord.Status)
        assert name == ServiceRecord.Status(value).name

    @pytest.mark.parametrize("s_port", [None, 12, "34"])
    def test_init(self, s_port):
        obj = ServiceRecord("some id", "aName", "Storage", "http", "127.0.0.1", s_port, 1234)
        assert isinstance(obj._id, str), f"Expected obj._id to be a string, but got {type(obj._id)}"
        assert "some id" == obj._id
        assert isinstance(obj._name, str), f"Expected obj._name to be a string, but got {type(obj._name)}"
        assert "aName" == obj._name
        assert isinstance(obj._type, str), f"Expected obj._type to be a string, but got {type(obj._type)}"
        assert "Storage" == obj._type
        assert obj._port is None or isinstance(obj._port, int), (f"Expected obj._port to be an integer, "
                                                                 f"but got {type(obj._port)}")
        assert int(s_port) == obj._port if s_port else obj._port is None
        assert isinstance(obj._management_port, int), (f"Expected obj._management_port to be an integer, "
                                                       f"but got {type(obj._management_port)}")
        assert 1234 == obj._management_port
        assert isinstance(obj._status, int), f"Expected obj._debug to be an integer, but got {type(obj._status)}"
        assert 1 == obj._status
        assert isinstance(obj._debug, dict), f"Expected obj._debug to be a dictionary, but got {type(obj._debug)}"
        assert {} == obj._debug , f"Expected obj._debug to be an empty dictionary, but got {repr(obj._debug)}"

    @pytest.mark.parametrize("s_type", [
        "Storage", "Core", "Southbound", "Notification", "Management", "Northbound", "Dispatcher",
        "BucketStorage", "Pipeline"])
    def test_init_with_valid_type(self, s_type):
        obj = ServiceRecord("some id", "aName", s_type, "http", "127.0.0.1", None, 1234)
        assert "some id" == obj._id
        assert "aName" == obj._name
        assert s_type == obj._type

    @pytest.mark.parametrize("s_type", [
        "", None, 12, "southbound", "south", "South", "North", "Filter", "External"
    ])
    def test_init_with_invalid_type(self, s_type):
        with pytest.raises(Exception) as ex:
            ServiceRecord("some id", "aName", s_type, "http", "127.0.0.1", None, 1234)
        assert ex.type is ServiceRecord.InvalidServiceType
