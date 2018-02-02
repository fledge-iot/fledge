#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Common module for the interaction with OSI OCS (OSIsoft Cloud Services) """

import requests
import json

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


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


def call_api(headers, tenant, name_space, api):
    """" Calls (read operation) an OCS api and returns a string representing the JSON response """

    tenant_url = "/api/Tenants/{}".format(tenant)
    api_url = "/Namespaces/{0}/{1}".format(name_space, api)
    url = "https://qi-data.osisoft.com" + tenant_url + api_url

    response = requests.get(url, headers=headers)

    api_output = response.json()

    api_output_str = json.dumps(api_output)

    return api_output_str
