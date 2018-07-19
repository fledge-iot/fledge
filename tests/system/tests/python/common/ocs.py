#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Common module for the interaction with OSI OCS (OSIsoft Cloud Services) """

import requests
import json

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

OCS_URL = "https://dat-a.osisoft.com"


def retrieve_authentication_token(tenant, client_id, client_secret,):
    """" Retrieves from OCS the authentication token for the requested tenant/client """

    url = 'https://login.windows.net/{0}/oauth2/token'.format(tenant)

    authorization = requests.post(
        url,
        data={
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'resource': 'https://qihomeprod.onmicrosoft.com/ocsapi'
        }
    )

    header = {
        'Authorization': 'bearer %s' % authorization.json()['access_token'],
        'Content-type': 'application/json',
        'Accept': 'text/plain'
    }

    return header


def delete_object(headers, tenant, namespace, _object):
    """" Deletes an OCS object, used against Types and Streams """

    tenant_url = "/api/Tenants/{}".format(tenant)
    api_url = "/Namespaces/{0}/{1}".format(namespace, _object)
    url = OCS_URL + tenant_url + api_url

    response = requests.delete(url, headers=headers)

    print('--- Deleted {} -----------------------------------------'.format(api_url))

    print('\nExit code: |{0}| \n\nText: |{1}| \n\nUrl: |{2}|   '.format(
        response.status_code,
        response.text,
        response.url,
    ))

    return response.text


def delete_object_type(headers, tenant, namespace, _type):
    """" Deletes all the items of a type, used for deleting Streams or/and Types """

    # Retrieves the list of objects to delete
    objects_list = call_api(headers, tenant, namespace, _type)

    if objects_list != "[]":
        # the translations are needed to being able to convert the string into a dict
        objects_list = objects_list.replace(": true", ": 1")
        objects_list = objects_list.replace(": false", ": 0")

        object_list_dict = eval(objects_list)
        print("\n Number of elements : namespace |{0}| - type |{1}| - N |{2}|".format(namespace,
                                                                                      _type,
                                                                                      len(object_list_dict)))

        for item in object_list_dict:
            type_to_del = item['Id']

            print("to delete |{}|".format(type_to_del))

            api = "{0}/{1}".format(_type, type_to_del)

            delete_object(headers, tenant, namespace, api)


def delete_types_streams(headers, tenant, namespace):
    """" Deletes all the types and streams in the provided namespace
         WARNING: it deletes all the information in the namespace
    """

    delete_object_type(headers, tenant, namespace, "Streams")

    delete_object_type(headers, tenant, namespace, "Types")


def call_api(headers, tenant, name_space, api):
    """" Calls (read operation) an OCS api and returns a string representing the JSON response """

    tenant_url = "/api/Tenants/{}".format(tenant)
    api_url = "/Namespaces/{0}/{1}".format(name_space, api)
    url = OCS_URL + tenant_url + api_url

    response = requests.get(url, headers=headers)

    api_output = response.json()

    api_output_str = json.dumps(api_output)

    return api_output_str


def get_values_stream(headers, tenant, namespace, ocs_stream, start_timestamp, values_count):
    """" Retrieves N values for a specific asset code """

    api_url = "Streams/{0}/Data/GetRangeValues?" \
              "startIndex={1}"\
              "&count={2}"\
              .format(ocs_stream,
                      start_timestamp,
                      values_count)

    api_output_str = call_api(headers, tenant, namespace, api_url)

    return api_output_str
