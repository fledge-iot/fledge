# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test Configuration REST API """

import os
import http.client
import json
from urllib.parse import quote
import time
from collections import Counter
import pytest
from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_DATA

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

cat_name = "Pub #1"
script_file_path = _FLEDGE_DATA + '/scripts/pub #1_item5_notify35.py' if _FLEDGE_DATA else _FLEDGE_ROOT + '/data/scripts/pub #1_item5_notify35.py'


class TestConfiguration:

    def test_default(self, fledge_url, reset_and_start_fledge, wait_time):
        # TODO: FOGL-2349, once resolved below remove file check will be deleted
        if os.path.exists(script_file_path):
            os.remove(script_file_path)

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/category')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc)

        # Utilities parent key creation
        time.sleep(wait_time)

        conn.request("GET", '/fledge/category?root=true')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        cats = jdoc["categories"]
        assert 3 == len(cats)
        assert {'key': 'Advanced', 'displayName': 'Advanced', 'description': 'Advanced'} == cats[0]
        assert {'key': 'General', 'displayName': 'General', 'description': 'General'} == cats[1]
        assert {'key': 'Utilities', 'displayName': 'Utilities', 'description': 'Utilities'} == cats[2]

        conn.request("GET", '/fledge/category?root=true&children=true')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 3 == len(jdoc["categories"])

        expected_with_utilities = [
            {'children': [{'children': [], 'displayName': 'Scheduler', 'key': 'SCHEDULER',
                           'description': 'Scheduler configuration'},
                          {'children': [], 'displayName': 'Service Monitor', 'key': 'SMNTR',
                           'description': 'Service Monitor'},
                          {'children': [{'children': [], 'displayName': 'sqlite', 'key': 'sqlite',
                           'description': 'Storage Plugin'}], 'displayName': 'Storage', 'key': 'Storage',
                           'description': 'Storage configuration'}],
             'displayName': 'Advanced', 'key': 'Advanced', 'description': 'Advanced'
             },
                        {'children': [{'children': [], 'key': 'Installation', 'description': 'Installation', 'displayName': 'Installation'},
                          {'children': [], 'displayName': 'Admin API', 'key': 'rest_api',
                           'description': 'Fledge Admin and User REST API'},
                          {'children': [], 'displayName': 'Fledge Service', 'key': 'service',
                           'description': 'Fledge Service'}
                          ],
             'displayName': 'General', 'key': 'General', 'description': 'General'
             },
            {'children': [],
             'displayName': 'Utilities', 'key': 'Utilities', 'description': 'Utilities'
             }
        ]

        assert expected_with_utilities == jdoc["categories"]

    def test_get_category(self, fledge_url):
        expected = {'httpsPort': {'displayName': 'HTTPS Port', 'description': 'Port to accept HTTPS connections on', 'type': 'integer', 'order': '3', 'value': '1995', 'default': '1995', 'validity': 'enableHttp=="false"'},
                    'authCertificateName': {'displayName': 'Auth Certificate', 'description': 'Auth Certificate name', 'type': 'string', 'order': '7', 'value': 'ca', 'default': 'ca'},
                    'certificateName': {'displayName': 'Certificate Name', 'description': 'Certificate file name', 'type': 'string', 'order': '4', 'value': 'fledge', 'default': 'fledge', 'validity': 'enableHttp=="false"'},
                    'authProviders': {'displayName': 'Auth Providers', 'description': 'Authentication providers to use for the interface (JSON array object)', 'type': 'JSON', 'order': '10', 'value': '{"providers": ["username", "ldap"] }', 'default': '{"providers": ["username", "ldap"] }'},
                    'passwordChange': {'displayName': 'Password Expiry Days', 'description': 'Number of days after which passwords must be changed', 'type': 'integer', 'order': '9', 'value': '0', 'default': '0'},
                    'authentication': {'displayName': 'Authentication', 'description': 'API Call Authentication', 'type': 'enumeration', 'options': ['mandatory', 'optional'], 'order': '5', 'value': 'optional', 'default': 'optional'},
                    'authMethod': {'displayName': 'Authentication method', 'description': 'Authentication method', 'type': 'enumeration', 'options': ['any', 'password', 'certificate'], 'order': '6', 'value': 'any', 'default': 'any'},
                    'httpPort': {'displayName': 'HTTP Port', 'description': 'Port to accept HTTP connections on', 'type': 'integer', 'order': '2', 'value': '8081', 'default': '8081'},
                    'allowPing': {'displayName': 'Allow Ping', 'description': 'Allow access to ping, regardless of the authentication required and authentication header', 'type': 'boolean', 'order': '8', 'value': 'true', 'default': 'true'},
                    'enableHttp': {'displayName': 'Enable HTTP', 'description': 'Enable HTTP (disable to use HTTPS)', 'type': 'boolean', 'order': '1', 'value': 'true', 'default': 'true'}}
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/category/rest_api')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc)
        assert Counter(expected) == Counter(jdoc)

    def test_create_category(self, fledge_url):
        payload = {'key': cat_name, 'description': 'a publisher', 'display_name': 'Publisher'}
        conf = {'item1': {'type': 'boolean', 'description': 'A Boolean check', 'default': 'False'},
                'item2': {'type': 'integer', 'description': 'An Integer check', 'default': '2'},
                'item3': {'type': 'password', 'description': 'A password check', 'default': 'Fledge'},
                'item4': {'type': 'string', 'description': 'A string check', 'default': 'fledge'},
                'item5': {'type': 'script', 'description': 'A script check', 'default': ''}
                }
        payload.update({'value': conf})
        conn = http.client.HTTPConnection(fledge_url)
        conn.request('POST', '/fledge/category', body=json.dumps(payload))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert cat_name == jdoc['key']
        assert "a publisher" == jdoc['description']
        assert "Publisher" == jdoc['displayName']
        expected_value = {'item1': {'type': 'boolean', 'default': 'false', 'value': 'false', 'description': 'A Boolean check'},
                          'item2': {'type': 'integer', 'description': 'An Integer check', 'default': '2', 'value': '2'},
                          'item3': {'type': 'password', 'description': 'A password check', 'default': 'Fledge', 'value': "****"},
                          'item4': {'type': 'string', 'description': 'A string check', 'default': 'fledge', 'value': 'fledge'},
                          'item5': {'type': 'script', 'description': 'A script check', 'default': '', 'value': ''}
                          }
        assert Counter(expected_value) == Counter(jdoc['value'])

    def test_get_category_item(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        encoded_url = '/fledge/category/{}/item1'.format(quote(cat_name))
        conn.request("GET", encoded_url)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'boolean' == jdoc['type']
        assert 'A Boolean check' == jdoc['description']
        assert 'false' == jdoc['value']

    def test_set_configuration_item(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        encoded_url = '/fledge/category/{}/item1'.format(quote(cat_name))
        conn.request("PUT", encoded_url, body=json.dumps({"value": "true"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'boolean' == jdoc['type']

        conn.request("GET", encoded_url)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'boolean' == jdoc['type']
        assert 'true' == jdoc['value']
        assert 'false' == jdoc['default']

    def test_update_configuration_item_bulk(self, fledge_url):
        expected = {'item1': {'default': 'false', 'value': 'false', 'description': 'A Boolean check', 'type': 'boolean'},
                    'item2': {'default': '2', 'value': '1', 'description': 'An Integer check', 'type': 'integer'},
                    'item3': {'default': 'Fledge', 'value': '****', 'description': 'A password check', 'type': 'password'},
                    'item4': {'default': 'fledge', 'value': 'new', 'description': 'A string check', 'type': 'string'},
                    'item5': {'type': 'script', 'description': 'A script check', 'default': '', 'value': ''}
                    }
        conn = http.client.HTTPConnection(fledge_url)
        encoded_url = '/fledge/category/{}'.format(quote(cat_name))
        conn.request("PUT", encoded_url, body=json.dumps({"item1": "false", "item2": "1", "item4": "new"}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert Counter(expected) == Counter(jdoc)

    @pytest.mark.skip(reason="Not in use")
    def test_add_configuration_item(self, fledge_url):
        pass

    def test_delete_configuration_item_value(self, fledge_url):
        expected = {'description': 'A string check', 'type': 'string', 'default': 'fledge', 'value': 'fledge'}
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", '/fledge/category/{}/item4/value'.format(quote(cat_name)))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert Counter(expected) == Counter(jdoc)

    def test_get_child_category(self, fledge_url):
        expected = [{'displayName': 'Installation', 'key': 'Installation', 'description': 'Installation'},
                    {'displayName': 'Admin API', 'key': 'rest_api', 'description': 'Fledge Admin and User REST API'},
                    {'displayName': 'Fledge Service', 'key': 'service', 'description': 'Fledge Service'}]
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", '/fledge/category/General/children')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 3 == len(jdoc["categories"])
        assert Counter({'categories': expected}) == Counter(jdoc)

    def test_create_child_category(self, fledge_url):
        payload = {'children': ['rest_api', 'service']}
        conn = http.client.HTTPConnection(fledge_url)
        encoded_url = '/fledge/category/{}/children'.format(quote(cat_name))
        conn.request('POST', encoded_url, body=json.dumps(payload))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert Counter(payload) == Counter(jdoc)

        expected_children = [{'key': 'rest_api', 'displayName': 'Admin API', 'description': 'Fledge Admin and User REST API'},
                             {'key': 'service', 'displayName': 'Fledge Service', 'description': 'Fledge Service'}]
        conn.request("GET", encoded_url)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 2 == len(jdoc['categories'])
        assert Counter({'categories': expected_children}) == Counter(jdoc)

    def test_delete_child_category(self, fledge_url):
        encoded_url = '/fledge/category/{}/children'.format(quote(cat_name))
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", encoded_url + '/rest_api')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert ['service'] == jdoc['children']

        expected_children = [{'key': 'service', 'displayName': 'Fledge Service', 'description': 'Fledge Service'}]
        conn.request("GET", encoded_url)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert expected_children == jdoc['categories']

    def test_delete_parent_category(self, fledge_url):
        encoded_url = '/fledge/category/{}'.format(quote(cat_name))
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", encoded_url + '/parent')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'Parent-child relationship for the parent-{} is deleted'.format(cat_name) == jdoc['message']

        conn.request("GET", encoded_url + '/children')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert [] == jdoc['categories']

    def test_upload_script(self, fledge_url):
        encoded_url = '/fledge/category/{}'.format(quote(cat_name))
        script_path = _FLEDGE_ROOT + '/tests/system/python/data/notify35.py'
        url = 'http://' + fledge_url + encoded_url + '/item5/upload'
        # Verify the API response keys
        upload_script = 'curl -s  -F "script=@{}" {}  | jq --raw-output ".value,.file,.default,.description,.type"'.format(script_path, url)
        exit_code = os.system(upload_script)
        assert 0 == exit_code
        expected = {'item4': {'value': 'fledge', 'default': 'fledge', 'type': 'string', 'description': 'A string check'},
                    'item5': {'default': '', 'value': 'import logging\nfrom logging.handlers import SysLogHandler\n\n\ndef notify35(message):\n    logger = logging.getLogger(__name__)\n    logger.setLevel(level=logging.INFO)\n    handler = SysLogHandler(address=\'/dev/log\')\n    logger.addHandler(handler)\n\n    logger.info("notify35 called with {}".format(message))\n    print("Notification alert: " + str(message))\n', 'file': script_file_path, 'type': 'script', 'description': 'A script check'},
                    'item3': {'value': '****', 'default': 'Fledge', 'type': 'password', 'description': 'A password check'},
                    'item1': {'value': 'false', 'default': 'false', 'type': 'boolean', 'description': 'A Boolean check'},
                    'item2': {'value': '1', 'default': '2', 'type': 'integer', 'description': 'An Integer check'}}
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("GET", encoded_url)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert Counter(expected) == Counter(jdoc)
        assert os.path.exists(script_file_path) is True

    def test_delete_category(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", '/fledge/category/{}'.format(quote(cat_name)))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'Category {} deleted successfully.'.format(cat_name) == jdoc['result']
        assert os.path.exists(script_file_path) is False
