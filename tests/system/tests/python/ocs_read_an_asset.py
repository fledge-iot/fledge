#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Retrieves x values of an OCS stream using the API GetRangeValues """

import common.ocs as ocs
import os
import sys

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


# ## Main ##############################################################################

if len(sys.argv) != 2:
    print("ERROR: OCS stream name is required as an input parameter")
    sys.exit(1)
else:
    ocs_stream = sys.argv[1]
    # asset_code = os.environ['ASSET_CODE']

tenant = os.environ['OCS_TENANT']
client_id = os.environ['OCS_CLIENT_ID']
client_secret = os.environ['OCS_CLIENT_SECRET']
namespace = os.environ['OCS_NAMESPACE']

start_timestamp = os.environ['START_TIMESTAMP']
values_count = os.environ['VALUES_COUNT']

headers = ocs.retrieve_authentication_token(tenant, client_id, client_secret)

api_output = ocs.get_values_stream(headers, tenant, namespace, ocs_stream, start_timestamp, values_count)

print("{0}".format(api_output))
