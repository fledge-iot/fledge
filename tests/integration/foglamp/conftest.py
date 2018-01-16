# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


def pytest_namespace():
    return {'test_env': {'address': '0.0.0.0', 'core_mgmt_port': 44039}}
