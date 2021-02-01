# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Command line JSON parsing utility Class"""

"""
module name: json_parse.py
This module reads JSON data from STDIN an parse it with argv[1] method
using optional match argv[2]

It prints the requested JSON value.
In case of errors it pronts the exception and returns 1 to the caller

Current implemented methods:
- get_rest_api_url() return the REST API url of Fledge
- get_category_item_default() returns the default value of a Fledge category name
- get_category_item_value() returns the value of a Fledge category name
- get_category_key() returns the match for a given category name
- get_schedule_id() returns the cheduled_id of a given schedule name
- get_current_schedule_id() returns the cheduled_id of new created schedule name
Usage:

$ echo $JSON_DATA | python3 -m json_parse $method_name $name
"""

__author__ = "Massimiliano Pinto"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

from enum import IntEnum
import sys
import json


# ExtractJson Class
class ExtractJson(object):
    def __init__(self, json_input, method):
        self._json = json_input
        self._method = method

    # Return REST API URL from 'Fledge' PID file in JSON input
    def get_rest_api_url_from_pid(self, unused=None):

        try:
            json_data = self._json['adminAPI']
            scheme = json_data['protocol'].lower()
            port = str(json_data['port'])
            if json_data['addresses'][0] == "0.0.0.0":
                address = "127.0.0.1"
            else:
                address = json_data['addresses'][0]

            return str(scheme + "://" + address + ":" + port)
        except Exception as ex:
            raise Exception(self.set_error_message("Fledge PID", ex))

    # Set error message for rasing exceptions class methods
    def set_error_message(self, name, ex):
        return ("Error parsing JSON '" + self._method + "', '" +
                name + "': " + ex.__class__.__name__ + ": " + str(ex))

    # Return REST API URL from 'Fledge Core' service in JSON input
    def get_rest_api_url(self, unused=None):
        try:
            scheme = self._json['services'][0]['protocol']
            port = str(self._json['services'][0]['service_port'])
            if self._json['services'][0]['address'] == "0.0.0.0":
                address = "127.0.0.1"
            else:
                address = self._json['services'][0]['address']

            return str(scheme + "://" + address + ":" + port)
        except Exception as ex:
            raise Exception(self.set_error_message("Fledge Core", ex))

    # Return the default value of a Fledge category item from JSON input
    def get_category_item_default(self, item):
        try:
            # Get the specified category item name
            cat_json = self._json

            return str(cat_json['value'][item]['default']).replace('"', '')
        except Exception as ex:
            raise Exception(self.set_error_message(name, ex))

    # Return the default value of a Fledge category item from JSON input
    def get_category_item_value(self, item):
        try:
            # Get the specified category item name
            cat_json = self._json

            return str(cat_json['value'][item]['value']).replace('"', '')
        except Exception as ex:
            raise Exception(self.set_error_message(name, ex))

    # Return the value of a Fledge category name from JSON input
    def get_category_key(self, key):
        try:
            # Get the specified category name
            cat_json = self._json

            # If no match return empty string
            if cat_json['key'] == key:
                return str(cat_json['key']).replace('"', '')
            else:
                return str("")
        except KeyError:
            raise Exception(self.set_error_message(name, ex))

    # Return the ID of a Fledge schedule name just created
    def get_current_schedule_id(self, name):
        try:
            # Get the specified schedule name
            schedule_json = self._json['schedule']

            if schedule_json['name'] == name:
                # Scheduler found, return the id
                return str(schedule_json['id'].replace('"', ''))
            else:
                # Name non found, return empty string
                return str("")

        except Exception as ex:
            raise Exception(self.set_error_message(name, ex))

    # Return the ID of a Fledge schedule name from JSON input with all schedules
    def get_schedule_id(self, name):
        try:
            # Get the specified schedule name
            schedules_json = self._json
            found = False

            # Look for _MATCH_SCHEDULE
            for schedule in schedules_json['schedules']:
                if schedule['name'] == name:
                    # Scheduler found, return the id
                    found = True
                    return str(schedule['id'].replace('"', ''))

            # Nothing has been found, return empty string
            return str("")

        except Exception as ex:
            raise Exception(self.set_error_message(name, ex))

# Main body
if __name__ == '__main__':
    try:
        # Read from STDIN
        read_data = sys.stdin.readline()

        method_name = str(sys.argv[1])

        # Instantiate the class with a JSON object from input data
        json_parse = ExtractJson(json.loads(read_data), method_name)

        # Build the class method to call using argv[1]
        if len(sys.argv) > 2:
            call_method = "json_parse." + method_name + "('" + str(sys.argv[2]) + "')"
        else:
            call_method = "json_parse." + method_name + "()"

        try:
            # Return the output
            output = eval(call_method)
            print(output)
        except Exception as ex:
            print("ERROR: " + str(ex))
            exit(1)

        # Return success
        exit(0)
    except AttributeError:
        print("ERROR: method '" + method_name + "' not implemented yet")
        # Return failure
        exit(1)
    except Exception as ex:
        if len(sys.argv) == 1:
            print("ERROR: " + str(ex))
        else:
            print("ERROR: '" + str(sys.argv[1]) + "', " + str(ex))
        # Return failure
        exit(1)
