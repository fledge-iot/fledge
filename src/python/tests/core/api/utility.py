# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import http.client
import json

__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

# Module attributes
__DB_NAME = "foglamp"
BASE_URL = 'localhost'
PORT = 8082


def _get_list_response_tree(add_url='/foglamp', node=None, search_key=None, data_element=None,
                            return_element=None):
    """
    Args:
        add_url: Endpoint of the request
        node: Key of the response node
        search_key: Key of the search parameter
        data_element: value to search
        return_element: values for this key is returned

    Returns:
           List containing the search element values for given key, Length of the list

    :Example:

        _get_list_response_tree(add_url='/foglamp/task', node='tasks', search_key='process_name', data_element='purge',
                    return_element='id')
        _get_list_response_tree(add_url='/foglamp/categories', node='categories', search_key='key',
                    data_element='COAP_CONF ', return_element='key')
    """
    conn = http.client.HTTPConnection(BASE_URL, port=PORT)
    conn.request("GET", add_url)
    r = conn.getresponse().read().decode()
    conn.close()
    retval = json.loads(r)
    l_occurances = []
    for elements in retval[node]:
        if elements[search_key] == data_element:
            l_occurances.append(elements[return_element])
    #print(u'All Occurrences {}'.format(l_occurances))
    #print(u'All Occurrences length {}'.format(len(l_occurances)))
    return len(l_occurances), l_occurances

