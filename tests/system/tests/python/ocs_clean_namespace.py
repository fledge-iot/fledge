#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Purges a Namespace deleting all the types and streams """

import common.ocs as ocs
import os

__author__ = "Stefano Simonelli"
__copyright__ = "Copyright (c) 2018 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


# ### Main ##############################################################################

tenant = os.environ['OCS_TENANT']
client_id = os.environ['OCS_CLIENT_ID']
client_secret = os.environ['OCS_CLIENT_SECRET']
namespace = os.environ['OCS_NAMESPACE']

headers = ocs.retrieve_authentication_token(tenant, client_id, client_secret)

ocs.delete_types_streams(headers, tenant, namespace)
