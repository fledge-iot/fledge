import logging
import foglamp.starter as starter

def main():
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("foglamp").setLevel(logging.DEBUG)

    starter.start()


if __name__ == "__main__":
    main()

