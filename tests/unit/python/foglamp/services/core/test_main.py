# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test server.Server.__main__ entry point

"""

import pytest
from unittest.mock import patch

from foglamp.services import core


@pytest.allure.feature("unit")
@pytest.allure.story("services", "core")
async def test_main():
    with patch('foglamp.services.core', return_value=None) as mockedMain:
        srvr = mockedMain.Server
        srvr.start.return_value = None

        srvr.start()

        srvr.start.assert_called_once_with()  # assert_called_once() is python3.6 onwards :]

        # Okay, let's verify once more! :P
        assert 1 == srvr.start.call_count
