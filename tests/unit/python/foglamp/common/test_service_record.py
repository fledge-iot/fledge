# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


""" Test foglamp/common/service_record.py """

import pytest

from foglamp.common.service_record import ServiceRecord

__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("common", "service-record")
class TestServiceRecord:

    @pytest.mark.parametrize("s_port", [None, 12, "34"])
    def test_init(self, s_port):
        obj = ServiceRecord("some id", "aName", "Storage", "http", "127.0.0.1", s_port, 1234)
        assert obj._id == "some id"
        assert obj._name == "aName"
        assert obj._type == "Storage"
        if s_port:
            assert obj._port == int(s_port)
        else:
            assert obj._port is None
        assert obj._management_port == 1234
        assert obj._status == 1

    @pytest.mark.parametrize("s_type", ["Storage", "Core", "Southbound"])
    def test_init_with_valid_type(self, s_type):
        obj = ServiceRecord("some id", "aName", s_type, "http", "127.0.0.1", None, 1234)
        assert obj._id == "some id"
        assert obj._name == "aName"
        assert obj._type == s_type

    def test_init_with_invalid_type(self):
        with pytest.raises(Exception) as excinfo:
            obj = ServiceRecord("some id", "aName", "BLAH", "http", "127.0.0.1", None, 1234)
        assert excinfo.type is ServiceRecord.InvalidServiceType
