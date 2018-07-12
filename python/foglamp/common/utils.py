# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""Common utilities"""


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
