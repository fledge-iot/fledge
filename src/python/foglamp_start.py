import logging

from foglamp.env import DbConfig
from foglamp.coap.server import CoAPServer


def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("foglamp").setLevel(logging.DEBUG)

    # set DB config
    DbConfig.initialize_config()
    # start coap Server
    CoAPServer.start()

if __name__ == "__main__":
    main()
