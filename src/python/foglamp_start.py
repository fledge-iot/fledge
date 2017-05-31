import logging
import foglamp.starter

def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("foglamp").setLevel(logging.DEBUG)

    forlamp.starter.start()


if __name__ == "__main__":
    main()

