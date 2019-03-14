# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Test Configuration REST API """


import http.client
import json
from urllib.parse import quote
import time

__author__ = "Praveen Garg"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


class TestConfiguration:

    def test_default(self, foglamp_url, reset_and_start_foglamp, wait_time):
        conn = http.client.HTTPConnection(foglamp_url)

        conn.request("GET", '/foglamp/category')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc)

        # Utilities parent key creation
        time.sleep(wait_time)

        conn.request("GET", '/foglamp/category?root=true')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        cats = jdoc["categories"]
        assert 3 == len(cats)
        assert {'key': 'General', 'displayName': 'General', 'description': 'General'} == cats[0]
        assert {'key': 'Advanced', 'displayName': 'Advanced', 'description': 'Advanced'} == cats[1]
        assert {'key': 'Utilities', 'displayName': 'Utilities', 'description': 'Utilities'} == cats[2]

        conn.request("GET", '/foglamp/category?root=true&children=true')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 3 == len(jdoc["categories"])

        expected_with_utilities = [
            {'children': [{'children': [], 'displayName': 'Admin API', 'key': 'rest_api',
                           'description': 'FogLAMP Admin and User REST API'},
                          {'children': [], 'displayName': 'FogLAMP Service', 'key': 'service',
                           'description': 'FogLAMP Service'}
                          ],
             'displayName': 'General', 'key': 'General', 'description': 'General'
             },
            {'children': [{'children': [], 'displayName': 'Scheduler', 'key': 'SCHEDULER',
                           'description': 'Scheduler configuration'},
                          {'children': [], 'displayName': 'Service Monitor', 'key': 'SMNTR',
                           'description': 'Service Monitor'}],
             'displayName': 'Advanced', 'key': 'Advanced', 'description': 'Advanced'
             },
            {'children': [],
             'displayName': 'Utilities', 'key': 'Utilities', 'description': 'Utilities'
             }
        ]

        assert expected_with_utilities == jdoc["categories"]

    def test_get_category(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("GET", '/foglamp/category/rest_api')
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert len(jdoc)
        for k, v in jdoc.items():
            assert 'type' in v
            assert 'value' in v
            assert 'default' in v
            assert 'description' in v

            assert 'displayName' in v

    def test_create_category(self, foglamp_url):
        payload = {'key': 'pub #1', 'description': 'a publisher', 'display_name': 'Pub #1'}
        conf = {'check': {'type': 'boolean', 'description': 'A Boolean check', 'default': 'False'}}
        payload.update({'value': conf})
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request('POST', '/foglamp/category', body=json.dumps(payload))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "pub #1" == jdoc['key']
        assert "a publisher" == jdoc['description']
        assert "Pub #1" == jdoc['displayName']
        expected_value = {'check': {
            'type': 'boolean', 'default': 'false', 'value': 'false', 'description': 'A Boolean check'}
        }
        assert expected_value == jdoc['value']

    def test_get_category_item(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        encoded_url = '/foglamp/category/{}/check'.format(quote('pub #1'))
        conn.request("GET", encoded_url)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'boolean' == jdoc['type']
        assert 'A Boolean check' == jdoc['description']
        assert 'false' == jdoc['value']

    def test_set_configuration_item(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        encoded_url = '/foglamp/category/{}/check'.format(quote('pub #1'))
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

    def test_update_configuration_item_bulk(self, foglamp_url):
        pass

    def test_add_configuration_item(self, foglamp_url):
        pass

    def test_delete_configuration_item_value(self, foglamp_url):
        pass

    def test_get_child_category(self, foglamp_url):
        pass

    def test_create_child_category(self, foglamp_url):
        pass

    def test_delete_child_category(self, foglamp_url):
        pass

    def test_delete_parent_category(self, foglamp_url):
        pass

    def test_upload_script(self, foglamp_url):
        pass
