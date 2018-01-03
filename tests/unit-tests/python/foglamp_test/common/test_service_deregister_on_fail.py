# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import pytest
import time
from . import foo

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# FIXME: Needs foglamp to start, and core mgt port

fs = None

name = "Foo"
core_host = "localhost"
core_port = "37061"


@pytest.allure.feature("common")
@pytest.allure.story("process")
class TestMicroservice:

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    # TODO: ideally it should have a ping; simulate / force failure
    def test_failed_service_get_unregistered(self):
        global fs
        fs = foo.get_instance(name, core_host, core_port)
        assert fs.microservice_id is not None

        res = fs.find_services(name='Foo')
        found = res["services"]
        assert 1 == len(found)

        svc = found[0]

        # as there is no ping
        assert 0 == svc["status"]

        # wait for 1s + monitor.py' _DEFAULT_SLEEP_INTERVAL
        time.sleep(1+5)

        res = fs.find_services(name='Foo')
        assert 400 == res["error"]["code"]
