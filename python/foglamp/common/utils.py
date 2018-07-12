# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common utilities"""

from foglamp.common.storage_client.payload_builder import PayloadBuilder

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


def check_reserved(string):
    """
    RFC 2396 Uniform Resource Identifiers (URI): Generic Syntax lists
    the following reserved characters.

    reserved    = ";" | "/" | "?" | ":" | "@" | "&" | "=" | "+" |
                  "$" | ","
    
    Hence for certain inputs, e.g. service name, configuration key etc which form part of a URL should not 
    contain any of the above reserved characters.
    
    :param string: 
    :return: 
    """
    reserved = ";" + "/" + "?" + ":" + "@" + "&" + "=" + "+" + "$" + ","
    if string is None or not isinstance(string, str) or string == "":
        return False
    for s in string:
        if s in reserved:
            return False
    return True


async def check_scheduled_processes(storage, process_name):
    payload = PayloadBuilder().SELECT("name").WHERE(['name', '=', process_name]).payload()
    result = await storage.query_tbl_with_payload('scheduled_processes', payload)
    return result['count']


async def check_schedules(storage, schedule_name):
    payload = PayloadBuilder().SELECT("schedule_name").WHERE(['schedule_name', '=', schedule_name]).payload()
    result = await storage.query_tbl_with_payload('schedules', payload)
    return result['count']


async def revert_scheduled_processes(storage, process_name):
    payload = PayloadBuilder().WHERE(['name', '=', process_name]).payload()
    await storage.delete_from_tbl('scheduled_processes', payload)


async def revert_configuration(storage, key):
    payload = PayloadBuilder().WHERE(['key', '=', key]).payload()
    await storage.delete_from_tbl('configuration', payload)