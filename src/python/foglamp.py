from foglamp.coap.server import CoAPServer
import logging

def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("foglamp").setLevel(logging.DEBUG)

    CoAPServer.start()

if __name__ == "__main__":
    main()

