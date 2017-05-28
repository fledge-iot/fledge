import logging
import foglamp.starter as start

def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("foglamp").setLevel(logging.DEBUG)

    start.start()


if __name__ == "__main__":
    main()

