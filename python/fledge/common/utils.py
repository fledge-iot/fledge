# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

"""Common utilities"""

import asyncio
import functools
import datetime

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import sys


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
    reserved = ";" + "/" + "?" + ":" + "@" + "&" + "=" + "+" + "$" + "," + "{" + "}"
    if string is None or not isinstance(string, str) or string == "":
        return False
    for s in string:
        if s in reserved:
            return False
    return True


def check_fledge_reserved(string):
    reserved = [
        'fledge',
        'general',
        'advanced',
        'notifications',
        'north',
        'south',
        'filter',
        'notify',
        'rule',
        'delivery',
        'utilities'
    ]
    if string is None or not isinstance(string, str) or string == "":
        return False
    if string.lower() in reserved:
        return False
    return True


def local_timestamp():
    """
    :return: str - current time stamp with microseconds and machine timezone info
    :example '2018-05-08 14:06:40.517313+05:30'
    """
    return str(datetime.datetime.now(datetime.timezone.utc).astimezone())


def add_functions_as_methods(functions):
    """ add_functions_as_methods - add the given functions to a class (to allow multi-file definition) 
        Type: class decorator
        Arguments:
            functions: list of functions (which expect a "self" argument) to be added to class namespace
    """
    
    def decorator(Class):
        for function in functions:
            setattr(Class, function.__name__, function)
        return Class
    return decorator


def eprint(*args, **kwargs):
    """ eprintf -- convenience print function that prints to stderr """
    print(*args, *kwargs, file=sys.stderr)


def read_os_release():
    """ General information to identifying the operating system """
    import ast
    import re
    os_details = {}
    with open('/etc/os-release', encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.rstrip()
            if not line or line.startswith('#'):
                continue
            m = re.match(r'([A-Z][A-Z_0-9]+)=(.*)', line)
            if m:
                name, val = m.groups()
                if val and val[0] in '"\'':
                    val = ast.literal_eval(val)
                os_details.update({name: val})
    return os_details


def is_redhat_based():
    """
        To check if the Operating system is of Red Hat family or Not
        Examples:
            a) For an operating system with "ID=centos", an assignment of "ID_LIKE="rhel fedora"" is appropriate
            b) For an operating system with "ID=ubuntu/raspbian", an assignment of "ID_LIKE=debian" is appropriate.
    """
    os_release = read_os_release()
    id_like = os_release.get('ID_LIKE')
    if id_like is not None and any(x in id_like.lower() for x in ['centos', 'rhel', 'redhat', 'fedora']):
        return True
    return False


def get_open_ssl_version(version_string=True):
    """ Open SSL version info

    Args:
        version_string

    Returns:
        When version_string is True - The version string of the OpenSSL library loaded by the interpreter
        When version_string is False - A tuple of five integers representing version information about the OpenSSL library
    """
    import ssl
    return ssl.OPENSSL_VERSION if version_string else ssl.OPENSSL_VERSION_INFO


def make_async(fn):
    """ turns a sync function to async function using threads """
    from concurrent.futures import ThreadPoolExecutor
    pool = ThreadPoolExecutor()

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        future = pool.submit(fn, *args, **kwargs)
        return asyncio.wrap_future(future)  # make it awaitable

    return wrapper


def dict_difference(dict1, dict2):
    """ Compare two dictionaries and return their difference """
    diff = {}

    # Check keys in dict1 not in dict2
    for key in dict1:
        if key not in dict2:
            diff[key] = dict1[key]
        else:
            # Recursively compare nested dictionaries
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                nested_diff = dict_difference(dict1[key], dict2[key])
                if nested_diff:
                    diff[key] = nested_diff
            elif dict1[key] != dict2[key]:
                diff[key] = dict1[key]

    # Check keys in dict2 not in dict1
    for key in dict2:
        if key not in dict1:
            diff[key] = dict2[key]
        else:
            # Recursively compare nested dictionaries
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                nested_diff = dict_difference(dict1[key], dict2[key])
                if nested_diff:
                    diff[key] = nested_diff
            elif dict1[key] != dict2[key]:
                diff[key] = dict2[key]
    return diff


def async_sleep(seconds):
    # Check Python version
    if sys.version_info < (3, 7):
        # For older versions, explicitly pass the loop argument
        loop = asyncio.get_event_loop()
        return asyncio.sleep(seconds, loop=loop)
    else:
        # For Python 3.7+, just use asyncio.sleep as usual
        return asyncio.sleep(seconds)

