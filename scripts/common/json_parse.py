# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Command line JSON parsing utility Class"""

import sys
import json


"""
module name: json_parse.py
This module reads JSON data from STDIN an parse it with argv[1] method
using optional match argv[2]

It prints the requested JSON value.
In case of errors it prints the exception and returns 1 to the caller

Current implemented methods:
- get_rest_api_url() return the REST API url of Fledge
- get_category_item_default() returns the default value of a Fledge category name
- get_category_item_value() returns the value of a Fledge category name
- get_category_key() returns the match for a given category name
- get_config_item_value() returns the configuration item value of a Fledge category name
- get_schedule_id() returns the scheduled_id of a given schedule name
- get_current_schedule_id() returns the scheduled_id of new created schedule name
Usage:

$ echo $JSON_DATA | python3 -m json_parse $method_name $name
"""

__author__ = "Massimiliano Pinto, Ashish Jabble"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


# ExtractJson Class
class ExtractJson(object):
    def __init__(self, json_input, method):
        self._json = json_input
        self._method = method

    # Set error message for raising exceptions class methods
    def set_error_message(self, name, err_exc):
        return "Error parsing JSON in method: {} for '{}' with exception {}:{}".format(
            self._method, name, err_exc.__class__.__name__, str(err_exc))

    # Return REST API URL from 'Fledge' PID file in JSON input
    def get_rest_api_url_from_pid(self, unused=None):
        try:
            json_data = self._json['adminAPI']
            scheme = json_data['protocol'].lower()
            port = str(json_data['port'])
            address = "127.0.0.1" if json_data['addresses'][0] == "0.0.0.0" else json_data['addresses'][0]
            url = "{}://{}:{}".format(scheme, address, port)
            return url
        except Exception as ex:
            raise Exception(self.set_error_message("Fledge PID", ex))

    # Return REST API URL from 'Fledge Core' service in JSON input
    def get_rest_api_url(self, unused=None):
        try:
            scheme = self._json['services'][0]['protocol']
            port = str(self._json['services'][0]['service_port'])
            address = "127.0.0.1" if self._json['services'][0]['address'] == "0.0.0.0" else \
                self._json['services'][0]['address']
            url = "{}://{}:{}".format(scheme, address, port)
            return url
        except Exception as ex:
            raise Exception(self.set_error_message("Fledge Core", ex))

    # Return the default value of a Fledge category item from JSON input
    def get_category_item_default(self, item):
        try:
            # Get the specified category item name
            cat_json = self._json
            return str(cat_json['value'][item]['default']).replace('"', '')
        except Exception as ex:
            raise Exception(self.set_error_message(item, ex))

    # Return the default value of a Fledge category item from JSON input
    def get_category_item_value(self, item):
        try:
            # Get the specified category item name
            cat_json = self._json
            return str(cat_json['value'][item]['value']).replace('"', '')
        except Exception as ex:
            raise Exception(self.set_error_message(item, ex))

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
        except KeyError as er:
            raise Exception(self.set_error_message(key, er))
        except Exception as ex:
            raise Exception(self.set_error_message(key, ex))

    # Return the value of configuration item of a Fledge category name
    def get_config_item_value(self, item):
        try:
            # Get the specified JSON
            cat_json = self._json
            return str(cat_json[item]['value']).replace('"', '')
        except Exception as ex:
            raise Exception(self.set_error_message(item, ex))

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
        except Exception as err:
            print("ERROR: " + str(err))
            exit(1)

        # Return success
        exit(0)
    except AttributeError:
        print("ERROR: method '" + method_name + "' not implemented yet")
        # Return failure
        exit(1)
    except Exception as exc:
        if len(sys.argv) == 1:
            print("ERROR: " + str(exc))
        else:
            print("ERROR: '" + str(sys.argv[1]) + "', " + str(exc))
        # Return failure
        exit(1)
