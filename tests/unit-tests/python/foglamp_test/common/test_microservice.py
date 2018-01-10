# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import pytest

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


@pytest.allure.feature("common")
@pytest.allure.story("microservice")
class TestMicroservice:

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    @pytest.mark.run('first')
    def test_start_and_register(self):
        global fs
        fs = foo.get_instance(name, core_host, core_port)
        assert fs._microservice_id is not None

        res = fs._core_microservice_management_client.get_services(name='Foo')
        found = res["services"]
        assert 1 == len(found)

    def test_get_service(self):
        res = fs._core_microservice_management_client.get_services(_type='Southbound')
        found = res["services"]
        is_found = False
        for f in found:
            if f["name"] == "Foo":
                is_found = True
                break

        assert True is is_found

        res = fs._core_microservice_management_client.get_services()
        found = res["services"]
        is_found = False
        for f in found:
            if f["name"] == "Foo":
                is_found = True
                break

        assert True is is_found

    def test_register_unregister_interest_in_category(self):
        res1 = fs._core_microservice_management_client.register_interest("blah1", fs._microservice_id)
        assert res1["id"] is not None
        res2 = fs._core_microservice_management_client.unregister_interest(res1["id"])
        assert res2["id"] == res1["id"]

    @pytest.mark.run('last')
    def test_shutdown_and_unregister(self):
        response = fs.shutdown()
        assert fs._microservice_id == response["id"]

        with pytest.raises(exceptions.MicroserviceManagementClientError) as exc_info:
            fs._core_microservice_management_client.get_services(name='Foo')
        exception_raised = exc_info.value
        assert 404 == exception_raised.status
        assert 'Service with name Foo does not exist' == exception_raised.reason
