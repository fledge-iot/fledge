#!/usr/bin/env python3

import argparse
import time

from foglamp.common import logger


""" To test scheduler """

_logger = logger.setup(__name__, level=20)

parser = argparse.ArgumentParser()
parser.add_argument("duration", help="sleep for seconds", type=int)
parser.add_argument("--address", help="address")
parser.add_argument("--port", help="port")
parser.add_argument("--name", help="name")
args = parser.parse_args()

_logger.info("sleeping for %s", args.duration)
time.sleep(args.duration)
