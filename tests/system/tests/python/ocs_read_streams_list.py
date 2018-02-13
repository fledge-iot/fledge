#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Retrieves the list of Streams defined in OCS for the specific Namespace """

import common.ocs as ocs
import os

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


# ## Main ##############################################################################

tenant = os.environ['OCS_TENANT']
client_id = os.environ['OCS_CLIENT_ID']
client_secret = os.environ['OCS_CLIENT_SECRET']
name_space = os.environ['OCS_NAMESPACE']

headers = ocs.retrieve_authentication_token(tenant, client_id, client_secret)

api = "Streams"
api_output = ocs.call_api(headers, tenant, name_space, api)

print("{0}".format(api_output))
