import foglamp.coap.register as coap
import foglamp.rest.register as rest
import asyncio


def start():
    coap.register()
    rest.register()

    asyncio.get_event_loop().run_forever()
