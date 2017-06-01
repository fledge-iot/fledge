#from foglamp.coap.sensor_values import SensorValues
import unittest
from unittest import mock
from unittest.mock import MagicMock
from cbor2 import dumps
import logging
import asyncio


from aiocoap import *

# use client to connect to coap server and upload payload.
#before you run this you need to start the coap server.
#
# ~/Development/FogLAMP/src/python$ ./build.sh --run
#
# testing commit.
#test 6

async def main():
    protocol = await Context.create_client_context()

    dict_payload = {'jack': 4098, 'sape': 4139}
    _payload = dumps(dict_payload)

    request = Message(code=Code.POST, uri='coap://localhost/other/sensor-values', payload=_payload)

    try:
        response = await protocol.request(request).response
    except Exception as e:
        print('Failed to fetch resource:')
        print(e)
    else:
        print('Result: %s\n%r'%(response.code, response.payload))

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())





print("all Done.");




