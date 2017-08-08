#!/usr/bin/env python3

# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END


""" fogbench -- a Python script used to test FogLAMP.

The objective is to simulate payloads for input, REST and other requests against one or
more FogLAMP instances. The initial version of fogbench is meant to test the sensor/device
interface of FogLAMP using CoAP.

fogbench

 [IN]   -h --help        Print this help
        -i --interval    The interval in seconds between each iteration (default: 0)
 [IN]   -k --keep        Do not delete (keep) the running sample (default: no)
 [IN]   -o --output      Set the output file
        -p --payload     Type of payload and protocol (default: sensor/coap)
        -t --template    Set the template to use
 [IN]   -v --version     Display the version and exit
        -H --host        The FogLAMP host (default: localhost)
        -I --iterations  The number of iterations of the test (default: 1)
        -O --occurrences The number of occurrences of the template (default: 1)
        -P --port        The FogLAMP port. Default depends on payload and protocol
        -S --statistic   The type of statistics to collect

 Example:

     $ cd benchmarks
     $ python -m fogbench

     or

     $ python -m benchmarks.fogbench

 Help:

     $ python -m fogbench -h

 .. todo::

   * Create reading objects from given template, as per the json file name specified with -t
   * Save those objects to the file, as per the file name specified with -o
   * Read those objects
   * Send those to CoAP sever, on specific host and port

   * Try generators

"""
import sys
import os
import random
import json
from datetime import datetime, timezone
import argparse
import uuid

import asyncio
from aiocoap import *
from cbor2 import dumps

# FIXME: remove relative import
from .exceptions import *

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_FOGBENCH_VERSION = u"0.1"
_START_TIME = ''
_END_TIME = ''
_TOT_MSGS_TRANSFERRED = 0
_TOT_BYTE_TRANSFERRED = 0
_NUM_ITERATED = 0

# TODO: have its own sys/ console logger
# _logger = logger.setup(__name__)


# TODO: move stuff to fogbench.py

def read_templates():
    templates = []

    # TODO: collect all the template json files
    # and pass to parse_template_and_prepare_json

    return templates


def parse_template_and_prepare_json(_template_file=u"fogbench_sensor_coap.template.json",
                                    _write_to_file=None, _occurrences=1):
    template_file = os.path.join(os.path.dirname(__file__), "templates/" + _template_file)

    with open(template_file) as data_file:
        data = json.load(data_file)
        # print(data)

    supported_format_types = ["number", "enum"]
    for d in data:
        x_sensor_values = dict()

        _sensor_value_object_formats = d["sensor_values"]
        for fmt in _sensor_value_object_formats:
            if fmt["type"] not in supported_format_types:
                raise InvalidSensorValueObjectTemplateFormat(u"Invalid format, "
                                                             u"Can not parse type {}".format(fmt["type"]))
            if fmt["type"] == "number":
                # check float precision if any
                precision = fmt.get("precision", None)
                min_val = fmt.get("min", None)
                max_val = fmt.get("max", None)
                if min_val is None or max_val is None:
                    raise InvalidSensorValueObjectTemplateFormat(u"Invalid format, "
                                                                 u"Min and Max values must be defined for type number.")
                # print(precision)
                # print(min_val)
                # print(max_val)
                reading = round(random.uniform(min_val, max_val), precision)
            elif fmt["type"] == "enum":
                reading = random.choice(fmt["list"])

            print(fmt["name"], reading)
            x_sensor_values[fmt["name"]] = reading

        # print(d["name"])

        sensor_value_object = dict()
        sensor_value_object["asset"] = d['name']
        sensor_value_object["sensor_values"] = x_sensor_values
        sensor_value_object["timestamp"] = "{!s}".format(datetime.now(tz=timezone.utc))
        sensor_value_object["key"] = str(uuid.uuid4())
        # print(json.dumps(sensor_value_object))

        temp_list = []
        # if _occurrences > 1:
        #     temp_list.append(sensor_value_object)

        with open(_write_to_file, 'a') as the_file:
            if len(temp_list):
                json.dump(temp_list*_occurrences, the_file)
            else:
                json.dump(sensor_value_object, the_file)
            the_file.write(os.linesep)


def read_out_file(_file=None, _keep=False, _iterations=1, _interval=0):
    global _START_TIME
    global _END_TIME
    global _TOT_MSGS_TRANSFERRED
    global _TOT_BYTE_TRANSFERRED
    global _NUM_ITERATED
    from pprint import pprint
    import time
    # _file = os.path.join(os.path.dirname(__file__), "out/{}".format(outfile))
    with open(_file) as f:
        readings_list = [json.loads(line) for line in f]
    pprint(readings_list)

    loop = asyncio.get_event_loop()

    _START_TIME = "{!s}".format(datetime.now(tz=timezone.utc))
    while _iterations > 0:
        # TODO: Fix key for next iteration
        for r in readings_list:
            loop.run_until_complete(send_to_coap(r))
            _TOT_MSGS_TRANSFERRED += 1
            _TOT_BYTE_TRANSFERRED += sys.getsizeof(r)
        _iterations -= 1
        _NUM_ITERATED += 1
        if _iterations != 0:
            print(u"Iteration {} completed, waiting for {} seconds".format(_iterations, _interval))
            time.sleep(_interval)
            # TODO: For next iteration, add time.sleep to payload timestamp
    _END_TIME = "{!s}".format(datetime.now(tz=timezone.utc))

    if not _keep:
        os.remove(_file)

async def send_to_coap(payload):
    """
    POST request to:
     localhost
     port 5683 (official IANA assigned CoAP port),
     URI "/other/sensor-values".

    Request is sent 2 seconds after initialization.
    """

    context = await Context.create_client_context()

    await asyncio.sleep(2)

    # request = Message(payload=dumps(payload), code=PUT)
    request = Message(payload=dumps(payload), code=POST)
    request.opt.uri_host = 'localhost'
    # request.opt.uri_path = ("other", "block")
    request.opt.uri_path = ("other", "sensor-values")
    response = await context.request(request).response

    # print('Result: %s\n%r' % (response.code, response.payload))
    print('Result: %s\n' % response.code)


def display_statistics(stats_type):
    print(u"{} statistics: ".format(stats_type))
    global _START_TIME
    global _END_TIME
    global _TOT_MSGS_TRANSFERRED
    global _TOT_BYTE_TRANSFERRED
    global _NUM_ITERATED
    if stats_type == 'total' or stats_type == 'st':
        print(u"Start Time::{}".format(_START_TIME))
    if stats_type == 'total' or stats_type == 'et':
        print(u"End Time::{}".format(_END_TIME))
    if stats_type == 'total' or stats_type == 'mt':
        print(u"Total Messages Transferred::{}".format(_TOT_MSGS_TRANSFERRED))
    if stats_type == 'total' or stats_type == 'bt':
        print(u"Total Bytes Transferred::{}".format(_TOT_BYTE_TRANSFERRED))
    if stats_type == 'total' or stats_type == 'itr':
        print(u"Total Iterations::{}".format(_NUM_ITERATED))
    if stats_type == 'total' or stats_type == 'mt_itr':
        print(u"Total Messages per Iteration::{}".format(_TOT_MSGS_TRANSFERRED/_NUM_ITERATED))
    if stats_type == 'total' or stats_type == 'bt_itr':
        print(u"Total Bytes per Iteration::{}".format(_TOT_BYTE_TRANSFERRED/_NUM_ITERATED))
    # TODO: Stats of Min, Avg Max msgs/sec bytes/sec per for all iterations


def check_coap_server():
    # TODO: Temporary info
    print(">>> $ python -m foglamp.device ; To see payload on console "
          "& ensure CoAP server is listening on {}:{}".format("localhost", 5683))

parser = argparse.ArgumentParser(prog='fogbench')
parser.description = '%(prog)s -- a Python script used to test FogLAMP (simulate payloads)'
parser.epilog = 'The initial version of %(prog)s is meant to test the sensor/device interface of FogLAMP using CoAP'
parser.add_argument('-v', '--version', action='version', version='%(prog)s {0!s}'.format(_FOGBENCH_VERSION))
parser.add_argument('-k', '--keep', default=False, choices=['y', 'yes', 'n', 'no'],
                    help='Do not delete the running sample (default: no)')
parser.add_argument('-o', '--output', help='set the output file, WITHOUT extension')

parser.add_argument('-I', '--iterations', help='The number of iterations of the test (default: 1)')
parser.add_argument('-O', '--occurrences', help='The number of occurrences of the template (default: 1)')

parser.add_argument('-H', '--host', help='CoAP server host address (default: localhost)', action=check_coap_server())
parser.add_argument('-i', '--interval', default=0, help='The interval in seconds for each iteration (default: 0)')

parser.add_argument('-S', '--statistics', default='total', choices=['total', 'st', 'et', 'mt', 'bt',
                                                                    'itr', 'mt_itr', 'bt_itr'], help='The type of statistics to collect (default: total)')

namespace = parser.parse_args(sys.argv[1:])

# could have set default in add_argument, but may be we don't want and this _1 is temp
# should use <template-name_timestamp> or <pid.json>  etc ...
outfile = '{0}.json'.format(namespace.output if namespace.output else '_1')
output_file = os.path.join(os.path.dirname(__file__), "out/{}".format(outfile))
keep_the_file = True if namespace.keep in ['y', 'yes'] else False

# iterations and occurrences
arg_iterations = int(namespace.iterations) if namespace.iterations else 1
arg_occurrences = int(namespace.occurrences) if namespace.occurrences else 1

# interval between each iteration
arg_interval = int(namespace.interval) if namespace.interval else 0

arg_stats_type = '{0}'.format(namespace.statistics) if namespace.statistics else 'total'

parse_template_and_prepare_json(_write_to_file=output_file, _occurrences=arg_occurrences)
read_out_file(_file=output_file, _keep=keep_the_file, _iterations=arg_iterations, _interval=arg_interval)  # and send to coap
display_statistics(arg_stats_type)

""" Expected output from given template
{ 
  "timestamp"     : "2017-08-04T06:59:57.503Z",
  "asset"         : "TI sensorTag/luxometer",
  "sensor_values" : { "lux" : 49 }
}

{ 
  "timestamp"     : "2017-08-04T06:59:57.863Z",
  "asset"         : "TI sensorTag/pressure",
  "sensor_values" : { "pressure" : 1021.2 }
}

{ 
  "timestamp"     : "2017-08-04T06:59:58.863Z",
  "asset"         : "TI sensorTag/humidity",
  "sensor_values" : { "humidity" : 71.2, "temperature" : 18.6 }
}

{ 
  "timestamp"     : "2017-08-04T06:59:59.863Z",
  "asset"         : "TI sensorTag/temperature",
  "sensor_values" : { "object" : 18.2, "ambient" : 21.6 }
}

{ 
  "timestamp"     : "2017-08-04T07:00:00.863Z",
  "asset"         : "TI sensorTag/accelerometer",
  "sensor_values" : { "x" : 1.2, "y" : 0.0, "z" : -0.6 }
}

{ 
  "timestamp"     : "2017-08-04T07:00:01.863Z",
  "asset"         : "TI sensorTag/gyroscope",
  "sensor_values" : { "x" : 101.2, "y" : 46.2, "z" : -12.6 }
}

{ 
  "timestamp"     : "2017-08-04T07:00:02.863Z",
  "asset"         : "TI sensorTag/magnetometer",
  "sensor_values" : { "x" : 101.2, "y" : 46.2, "z" : -12.6 }
}

{ 
  "timestamp"     : "2017-08-04T07:00:03.863Z",
  "asset"         : "mouse",
  "sensor_values" : { "button" : "down" }
}

{ 
  "timestamp"     : "2017-08-04T07:00:04.863Z",
  "asset"         : "wall clock",
  "sensor_values" : { "tick" : "tock" }
}

"""
