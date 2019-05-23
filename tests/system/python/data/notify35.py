import logging
from logging.handlers import SysLogHandler


def notify35(message):
    logger = logging.getLogger(__name__)
    logger.setLevel(level=logging.INFO)
    handler = SysLogHandler(address='/dev/log')
    logger.addHandler(handler)

    logger.info("notify35 called with {}".format(message))
    print("Notification alert: " + str(message))
