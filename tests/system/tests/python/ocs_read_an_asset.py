#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2018 ihs

"""" OCS tool-set V 1.7 """

# noinspection PyPackageRequirements
import requests

def call_ocs_api(api, api_url, print_output=True):
    """" Call (read operation) an OCS api """

    response = requests.get('https://qi-data.osisoft.com' + tenant + api_url, headers=headers)

    if print_output:
        print('--- {} -----------------------------------------'.format(api))

        print('\nExit code: |{0}| \n\nText: |{1}| \n\nUrl: |{2}|   '.format(
            response.status_code,
            response.text,
            response.url,
        ))

    return response.text


def call_ocs_api_delete(api, api_url):
    """" Deletes an OCS object, used against Streams or Types """

    response = requests.delete('https://qi-data.osisoft.com' + tenant + api_url, headers=headers)

    print('--- {} -----------------------------------------'.format(api))

    print('\nExit code: |{0}| \n\nText: |{1}| \n\nUrl: |{2}|   '.format(
        response.status_code,
        response.text,
        response.url,
    ))

    return response.text


def delete_object_type(namespace, _type):
    """" Deletes all the items of a type, used for deleting Streams or/and Types """

    # Delete Types
    _values = call_ocs_api(_type, "/Namespaces/{0}/{1}".format(namespace, _type))

    # Translation needed
    _values = _values.replace(":true", ":1")

    value_dict = eval(_values)
    print("\n Number of elements : namespace |{0}| - type |{1}| - N |{2}|".format(namespace, _type, len(value_dict)))

    for item in value_dict:
        type_to_del = item['Id']

        print("To del |{}|".format(type_to_del))

        url = "/Namespaces/{0}/{1}/{2}".format(namespace, _type, type_to_del)
        call_ocs_api_delete("{0} - Delete".format(_type), url)


def delete_streams_types(namespace):
    """" Deletes all the streams and types in the provided namespace
        WARNING: it deletes all the information in the Namespace
    """

    # Delete Streams
    delete_object_type(namespace, "Streams")

    delete_object_type(namespace, "Types")


def get_values_stream(namespace, asset_code, timestamp, num_values):
    """" Retrieves N values for an asset code """

    _values = call_ocs_api(
                            "GetRangeValues",
                            "/Namespaces/{0}/Streams/measurement_{1}/Data/GetRangeValues?"
                            "startIndex={2}"
                            "&count={3}"
                            # &reversed=true
                            "".format(namespace, asset_code, timestamp, num_values)
                            )

    print_values(_values)


def print_values(_values):
    """" Print values returned but OCS API """

    # Translation needed
    _values = _values.replace(":true", ":1")

    if _values:
        value_dict = eval(_values)
        print("\n Number of elements {}".format(len(value_dict)))

        for item in value_dict:

            print("--------------------------------------------------")
            for key in item:
                print("Information |{} - |{}|".format(key, item[key]))


# ## OCS API - Authorization handling ##############################################################################

authorization = requests.post(
            'https://login.windows.net/4be9ded8-c6a6-44ac-8e1a-9db44e58fa49/oauth2/token',
            data={
                    'grant_type': 'client_credentials',
                    'client_id': '34571f14-d7d5-4cee-aaf6-0a5395bb6a10',
                    'client_secret': 'Ia9xCiRNuCiiCv793M7EU24KNT5re+Gfwg2ABwoPfAY=',
                    'resource': 'https://qihomeprod.onmicrosoft.com/ocsapi'
                    }
        )

headers = {
            'Authorization': 'bearer %s' % authorization.json()['access_token'],
            'Content-type': 'application/json',
            'Accept': 'text/plain'
            }

# Dianomic tenant
tenant = "/api/Tenants/4be9ded8-c6a6-44ac-8e1a-9db44e58fa49"

# ### Setup #########################################################################################:

name_space = "test_19"

# ### Read - operations #########################################################################################:
# fogbench_luxometer
# fogbench_accelerometer

get_values_stream(name_space, "fogbench_smoke_test", "2018-01-01T09:25:20.670404Z", 1000)
