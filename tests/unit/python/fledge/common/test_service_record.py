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


@pytest.allure.feature("unit")
@pytest.allure.story("common", "service-record")
class TestServiceRecord:

    @pytest.mark.parametrize("s_port", [None, 12, "34"])
    def test_init(self, s_port):
        obj = ServiceRecord("some id", "aName", "Storage", "http", "127.0.0.1", s_port, 1234)
        assert "some id" == obj._id
        assert "aName" == obj._name
        assert "Storage" == obj._type
        if s_port:
            assert int(s_port) == obj._port
        else:
            assert obj._port is None
        assert 1234 == obj._management_port
        assert 1 == obj._status

    @pytest.mark.parametrize("s_type", ["Storage", "Core", "Southbound"])
    def test_init_with_valid_type(self, s_type):
        obj = ServiceRecord("some id", "aName", s_type, "http", "127.0.0.1", None, 1234)
        assert "some id" == obj._id
        assert "aName" == obj._name
        assert s_type == obj._type

    def test_init_with_invalid_type(self):
        with pytest.raises(Exception) as excinfo:
            obj = ServiceRecord("some id", "aName", "BLAH", "http", "127.0.0.1", None, 1234)
        assert excinfo.type is ServiceRecord.InvalidServiceType
