# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test services/south/__main__ entry point

"""

import pytest
from foglamp.services.south import __main__ as south_main
from foglamp.services.common.microservice import FoglampMicroservice


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("services", "south")
@pytest.mark.asyncio
async def test_south_main(mocker):
    # GIVEN
    mocker.patch.object(FoglampMicroservice, "__init__", return_value=None)
    south_server = south_main.Server()
    mock_run = mocker.patch.object(south_server, "run", return_value=None)

    # WHEN
    south_server.run()

    # THEN
    mock_run.assert_called_once_with()
    assert 1 == mock_run.call_count
