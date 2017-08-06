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

 -h --help        Print this help
 -i --interval    The interval in seconds between each iteration (default: 0)
 -k --keep        Do not delete (keep) the running sample (default: no)
 -o --output      Set the output file
 -p --payload     Type of payload and protocol (default: sensor/coap)
 -t --template    Set the template to use
 -v --version     Display the version and exit
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

 .. todo::

   * Create reading objects from given template, as per the json file name specified with -t
   * Save those objects to the file, as per the file name specified with -o
   * Read those objects
   * Send those to CoAP sever, on specific host and port

   * Try generators

"""
import os
import random
import json
from datetime import datetime, timezone

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
# TODO: have its own sys/ console logger
# _logger = logger.setup(__name__)


# TODO: move stuff to fogbench.py

def read_templates():
    templates = []

    # TODO: collect all the template json files
    # and pass to parse_template_and_prepare_json

    return templates


def parse_template_and_prepare_json(file_name=u"fogbench_sensor_coap.template.json"):
    template_file = os.path.join(os.path.dirname(__file__), "templates/"+file_name)

    with open(template_file) as data_file:
        data = json.load(data_file)

    # print(data)

    for d in data:
        _sensor_value_object_formats = d["sensor_values"]
        x_sensor_values = dict()

        for fmt in _sensor_value_object_formats:
            if fmt["type"] == "number":
                # check float precision if any
                precision = fmt.get("precision", 0)
                min_val = fmt.get("min", None)
                max_val = fmt.get("max", None)
                if min_val is None or max_val is None:
                    raise InvalidSensorValueObjectTemplateFormat(u"Invalid format, "
                                                         u"Min and Max values must be defined for type number.")
                # print(precision)
                # print(min_val)
                # print(max_val)
                reading = round(random.uniform(min_val, max_val), precision)
                # print(reading)
            elif fmt["type"] == "enum":
                reading = random.choice(fmt["list"])

            # print(fmt["name"])
            x_sensor_values[fmt["name"]] = reading

        # print(d["name"])

        sensor_value_object = dict()
        sensor_value_object["asset"] = d['name']
        sensor_value_object["sensor_values"] = x_sensor_values
        sensor_value_object["timestamp"] = "{!s}".format(datetime.now(tz=timezone.utc))

        # print(json.dumps(sensor_value_object))

        write_to_file = os.path.join(os.path.dirname(__file__), "out/_1.json")
        with open(write_to_file, 'a') as the_file:
            json.dump(sensor_value_object, the_file)
            the_file.write(os.linesep)


def read_out_file():
    from pprint import pprint
    write_to_file = os.path.join(os.path.dirname(__file__), "out/_1.json")
    with open(write_to_file) as f:
        readings_list = [json.loads(line) for line in f]
    pprint(readings_list)

    loop = asyncio.get_event_loop()

    for r in readings_list:
        loop.run_until_complete(send_to_coap(r))


async def send_to_coap(payload):
    """
    PUT request to localhost
    port 5683 (official IANA assigned CoAP port), URI "/other/block".
    Request is sent 2 seconds after initialization.

    Payload is bigger than 1kB, and thus is sent as several blocks.
    """

    context = await Context.create_client_context()

    await asyncio.sleep(2)

    # payload = b"some blah text ....\n" * 30

    request = Message(payload=dumps(payload), code=PUT)
    request.opt.uri_host = 'localhost'
    request.opt.uri_path = ("other", "block")
    # request.opt.uri_path = (".well-known", "core")
    response = await context.request(request).response

    print('Result: %s\n%r'%(response.code, response.payload))


parse_template_and_prepare_json()
read_out_file()  # and send to coap

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
