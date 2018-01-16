# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


def pytest_namespace():
    return {'test_env': {'core_mgmt_port': 39687}}
