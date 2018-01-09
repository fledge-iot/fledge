# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import pytest
import time

from . import foo
from foglamp.common.microservice_management_client import exceptions

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# FIXME: Needs foglamp to start, and core mgt port

fs = None

name = "Foo"
core_host = "localhost"
core_port = "34134"


@pytest.allure.feature("core")
@pytest.allure.story("monitor")
class TestMonitoring:

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    # TODO: ideally it should have a ping; simulate / force failure
    def test_failed_service_get_unregistered(self):
        global fs
        fs = foo.get_instance(name, core_host, core_port)
        assert fs._microservice_id is not None

        res = fs._core_microservice_management_client.get_services(name='Foo')
        found = res["services"]
        assert 1 == len(found)

        svc = found[0]
        assert 1 == svc["status"]

        # NO! test must not wait for such a long; Use test double?!
        # wait for 1s + monitor.py' _DEFAULT_SLEEP_INTERVAL + attempts*sleep
        time.sleep(1+5+15)  # fix me as per attempts and sleep total

        # NO PING?

        with pytest.raises(exceptions.MicroserviceManagementClientError) as exc_info:
            fs._core_microservice_management_client.get_services(name='Foo')
        exception_raised = exc_info.value
        assert 404 == exception_raised.status
        assert 'Service with name Foo does not exist' == exception_raised.reason
