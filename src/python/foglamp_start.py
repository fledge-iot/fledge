import logging

from foglamp.configurator import Configurator
from foglamp.coap.server import CoAPServer


def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("foglamp").setLevel(logging.DEBUG)

    # set DB config
    Configurator().initialize_dbconfig()
    # start coap Server
    CoAPServer.start()

if __name__ == "__main__":
    main()
