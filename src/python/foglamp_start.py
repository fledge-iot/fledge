import logging

import foglamp.coap as coap
import foglamp.rest as rest
import asyncio

def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("foglamp").setLevel(logging.DEBUG)

    coap.register()
    rest.register()

    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    main()

