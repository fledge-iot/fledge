# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test server.Server.__main__ entry point

"""

import pytest
from unittest.mock import patch

from fledge.services import core


@pytest.allure.feature("unit")
@pytest.allure.story("services", "core")
async def test_main():
    with patch('fledge.services.core', return_value=None) as mockedMain:
        srvr = mockedMain.Server
        srvr.start.return_value = None

        srvr.start()

        srvr.start.assert_called_once_with()  # assert_called_once() is python3.6 onwards :]

        # Okay, let's verify once more! :P
        assert 1 == srvr.start.call_count
