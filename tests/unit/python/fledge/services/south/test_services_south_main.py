# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test services/south/__main__ entry point

"""

import pytest
from fledge.services.south import __main__ as south_main
from fledge.services.common.microservice import FledgeMicroservice


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("services", "south")
@pytest.mark.asyncio
async def test_south_main(mocker):
    # GIVEN
    mocker.patch.object(FledgeMicroservice, "__init__", return_value=None)
    south_server = south_main.Server()
    mock_run = mocker.patch.object(south_server, "run", return_value=None)

    # WHEN
    south_server.run()

    # THEN
    mock_run.assert_called_once_with()
    assert 1 == mock_run.call_count
