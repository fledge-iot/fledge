#!/usr/bin/env python3

# -*- coding: utf-8 -*-

""" This module is for test purpose only!

This must go away when tests and actually STORAGE layer (FOGL-197) are in place

"""

from foglamp.core.service_registry.service_registry import Service

from foglamp.storage.storage import Storage, Readings
from foglamp.storage import exceptions

# register the service to test the code
Service.Instances.register(name="store", s_type="Storage", address="blah", port=81)

# discover the Storage type the service: how do we know the instance name?
# with type there can be multiple instances
# TODO: do get via REST api
storage_svc = Service.Instances.get(name="store")[0]

if not storage_svc:
    raise exceptions.StorageServiceUnavailableException
print(storage_svc)


# manually disconnect
conn1 = Storage(storage_svc).connect()
Readings.append(conn1, readings=["a", "b"])

# with context
with Storage(storage_svc) as conn2:
    Readings.append(conn2, readings=["c", "d"])
