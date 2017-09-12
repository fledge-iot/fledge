# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Unit test for foglamp.device.coap"""

import pytest
from unittest.mock import MagicMock
from aiocoap.numbers.codes import Code as CoAP_CODES
from cbor2 import dumps

from foglamp.device.coap import CoAPIngest
from foglamp.device.ingest import Ingest

__author__ = "Terris Linenbach"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


@pytest.allure.feature("unit")
@pytest.allure.story("device")
class TestIngestReadings(object):
    """Unit tests for foglamp.device.coap.IngestReadings
    """
    __REQUESTS = [
        ("bad request", CoAP_CODES.BAD_REQUEST),
        ({'timestamp': 'bad timestamp', 'asset': 'test'}, CoAP_CODES.BAD_REQUEST),
        ({'timestamp': '2017-01-01T00:00:00Z', 'asset': 'test',
          'readings': 5}, CoAP_CODES.BAD_REQUEST),
        ({'timestamp': '2017-01-01T00:00:00Z', 'asset': 'test', 'key': 5}, CoAP_CODES.BAD_REQUEST),
        ({'asset': 'test'}, CoAP_CODES.BAD_REQUEST),
        ({'timestamp': '2017-01-01T00:00:00Z', 'asset': 'test'}, CoAP_CODES.VALID),
        ({'timestamp': '2017-01-01T00:00:00Z', 'asset': 'test',
          'key': '123e4567-e89b-12d3-a456-426655440000'}, CoAP_CODES.VALID),
        ({'timestamp': '2017-01-01T00:00:00Z', 'asset': 'test'}, CoAP_CODES.VALID),
        ({'timestamp': '2017-01-01T00:00:00Z', 'asset': 'test2',
         'readings': {'a': 5}}, CoAP_CODES.VALID),
        ({}, CoAP_CODES.BAD_REQUEST),
        ({'timestamp': '2017-01-01T00:00:00Z'}, CoAP_CODES.BAD_REQUEST),
        ({'timestamp': 5}, CoAP_CODES.BAD_REQUEST),
    ]
    """An array of (payload, expected status code)
    """

    @pytest.mark.parametrize("payload, expected", __REQUESTS)
    @pytest.mark.asyncio
    async def test_payload(self, payload, expected):
        """Runs all test cases in the __REQUESTS array"""
        await Ingest.start()

        sv = CoAPIngest()
        request = MagicMock()
        request.payload = dumps(payload)
        repeat = 10 if expected == CoAP_CODES.VALID else 1
        for _ in range(repeat):
            return_val = await sv.render_post(request)
            assert return_val.code == expected

        await Ingest.stop()

    @pytest.mark.asyncio
    async def test_bad_cbor(self):
        await Ingest.start()

        sv = CoAPIngest()
        request = MagicMock()
        request.payload = 5
        return_val = await sv.render_post(request)
        assert return_val.code == CoAP_CODES.BAD_REQUEST

        await Ingest.stop()
