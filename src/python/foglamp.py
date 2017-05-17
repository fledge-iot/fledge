import asyncio
import logging
from foglamp.coap.server import CoAPServer

logging.basicConfig(level=logging.INFO)
logging.getLogger("foglamp").setLevel(logging.DEBUG)

def main():
    CoAPServer.start()
    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    main()

