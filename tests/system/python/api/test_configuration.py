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

__author__ = "Praveen Garg, Ashish Jabble"
__copyright__ = "Copyright (c) 2025 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

cat_name = "Pub #1"
script_file_path = _FLEDGE_DATA + '/scripts/pub #1_item5_notify35.py' if _FLEDGE_DATA else _FLEDGE_ROOT + '/data/scripts/pub #1_item5_notify35.py'


class TestConfiguration:

    def test_default(self, fledge_url, reset_and_start_fledge, wait_time, storage_plugin):
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
          {
              'key': 'Advanced',
              'description': 'Advanced',
              'displayName': 'Advanced',
              'children': [
                  {
                            'key': 'Storage',
                            'description': 'Storage configuration',
                            'displayName': 'Storage',
                            'children': [
                                {
                                  'key': storage_plugin,
                                  'description': 'Storage Plugin',
                                  'displayName': storage_plugin,
                                  'children': []
                                }
                            ]
                  },
                  {
                     'key': 'SMNTR',
                     'description': 'Service Monitor',
                     'displayName': 'Service Monitor',
                     'children': []
                  },
                  {
                     'key': 'SCHEDULER',
                     'description': 'Scheduler configuration',
                     'displayName': 'Scheduler',
                     'children': []
                  },
                  {
                      "key": "LOGGING",
                      "description": "Logging Level of Core Server",
                      "displayName": "Logging",
                      'children': []
                  },
                  {
                      "key": "RESOURCE_LIMIT",
                      "description": "Resource Limit of South Service",
                      "displayName": "Resource Limit",
                      "children": []
                  },
                  {
                      'key': 'CONFIGURATION',
                      'description': 'Core Configuration Manager',
                      'displayName': 'Configuration Manager',
                      'children': []
                  },
                  {
                      'key': 'FEATURES',
                      'description': 'Control the inclusion of system features',
                      'displayName': 'Features',
                      'children': []
                  }
              ]
          },
          {
                     'key': 'General',
                     'description': 'General',
                     'displayName': 'General',
                     'children': [
                         {
                             'key': 'service',
                             'description': 'Fledge Service',
                             'displayName': 'Fledge Service',
                             'children': []
                         },
                         {
                             'key': 'rest_api',
                             'description': 'Fledge Admin and User REST API',
                             'displayName': 'Admin API',
                             'children': [
                                 {
                                     "key": "password",
                                     "description": "To control the password policy",
                                     "displayName": "Password Policy",
                                     "children": [

                                     ]
                                 },
                                 {
                                     "key": "firewall",
                                     "description": "Monitor and Control HTTP Network Traffic",
                                     "displayName": "Firewall",
                                     "children": [

                                     ]
                                 }
                             ]
                         },
                         {
                              'key': 'Installation',
                              'description': 'Installation',
                              'displayName': 'Installation',
                              'children': []
                         }
                     ]
            },
            {
                          'key': 'Utilities',
                          'description': 'Utilities',
                          'displayName': 'Utilities',
                          'children': [
                              {
                                  'key': 'purge_system',
                                  'description': 'Configuration of the Purge System',
                                  'displayName': 'Purge System',
                                  'children': []
                              },
                              {
                                  'key': 'PURGE_READ',
                                  'description': 'Purge the readings, log, statistics history table',
                                  'displayName': 'Purge',
                                  'children': []
                              }
                          ]
            }
        ]

        assert expected_with_utilities == jdoc["categories"]

    def test_get_category(self, fledge_url):
        expected = {'httpsPort': {'displayName': 'HTTPS Port', 'description': 'Port to accept HTTPS connections on', 'type': 'integer', 'order': '3', 'value': '1995', 'default': '1995', 'validity': 'enableHttp=="false"', 'permissions': ['admin']},
                    'authCertificateName': {'displayName': 'Auth Certificate', 'description': 'Auth Certificate name', 'type': 'string', 'order': '7', 'value': 'ca', 'default': 'ca', 'permissions': ['admin']},
                    'certificateName': {'displayName': 'Certificate Name', 'description': 'Certificate file name', 'type': 'string', 'order': '4', 'value': 'fledge', 'default': 'fledge', 'validity': 'enableHttp=="false"', 'permissions': ['admin']},
                    'authProviders': {'displayName': 'Auth Providers', 'description': 'Authentication providers to use for the interface (JSON array object)', 'type': 'JSON', 'order': '9', 'value': '{"providers": ["username", "ldap"] }', 'default': '{"providers": ["username", "ldap"] }', 'permissions': ['admin']},
                    'authentication': {'displayName': 'Authentication', 'description': 'API Call Authentication', 'type': 'enumeration', 'options': ['mandatory', 'optional'], 'order': '5', 'value': 'optional', 'default': 'optional', 'permissions': ['admin']},
                    'authMethod': {'displayName': 'Authentication method', 'description': 'Authentication method', 'type': 'enumeration', 'options': ['any', 'password', 'certificate'], 'order': '6', 'value': 'any', 'default': 'any', 'permissions': ['admin']},
                    'httpPort': {'displayName': 'HTTP Port', 'description': 'Port to accept HTTP connections on', 'type': 'integer', 'order': '2', 'value': '8081', 'default': '8081', 'permissions': ['admin']},
                    'allowPing': {'displayName': 'Allow Ping', 'description': 'Allow access to ping, regardless of the authentication required and authentication header', 'type': 'boolean', 'order': '8', 'value': 'true', 'default': 'true', 'permissions': ['admin']},
                    'enableHttp': {'displayName': 'Enable HTTP', 'description': 'Enable HTTP (disable to use HTTPS)', 'type': 'boolean', 'order': '1', 'value': 'true', 'default': 'true', 'permissions': ['admin']},
                    'disconnectIdleUserSession': {'description': 'Disconnect idle user session after certain period of inactivity', 'type': 'integer', 'default': '15', 'displayName': 'Idle User Session Disconnection (In Minutes)', 'order': '10', 'minimum': '1', 'maximum': '1440', 'value': '15', 'permissions': ['admin']}}
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
                'item5': {'type': 'script', 'description': 'A script check', 'default': ''},
                'item6': {'type': 'string', 'description': 'A string check', 'default': 'test', 'group': 'Advanced'}
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
        expected_value = {
            'item1': {'type': 'boolean', 'default': 'false', 'value': 'false', 'description': 'A Boolean check'},
            'item2': {'type': 'integer', 'description': 'An Integer check', 'default': '2', 'value': '2'},
            'item3': {'type': 'password', 'description': 'A password check', 'default': 'Fledge', 'value': "****"},
            'item4': {'type': 'string', 'description': 'A string check', 'default': 'fledge', 'value': 'fledge'},
            'item5': {'type': 'script', 'description': 'A script check', 'default': '', 'value': ''},
            'item6': {'type': 'string', 'description': 'A string check', 'default': 'test', 'value': 'test',
                      'group': 'Advanced'}
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

        # Get optional attribute
        encoded_url = '/fledge/category/{}/item6'.format(quote(cat_name))
        conn.request("GET", encoded_url)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'string' == jdoc['type']
        assert 'Advanced' == jdoc['group']

    def test_set_configuration_item(self, fledge_url):
        new_value = "true"
        conn = http.client.HTTPConnection(fledge_url)
        encoded_url = '/fledge/category/{}/item1'.format(quote(cat_name))
        conn.request("PUT", encoded_url, body=json.dumps({"value": new_value}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'boolean' == jdoc['type']
        assert new_value == jdoc['value']
        assert 'false' == jdoc['default']

        # Verify new value in GET endpoint
        conn.request("GET", encoded_url)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'boolean' == jdoc['type']
        assert new_value == jdoc['value']
        assert 'false' == jdoc['default']

        # set optional attribute
        new_val = "Security"
        encoded_url = '/fledge/category/{}/item6'.format(quote(cat_name))
        conn.request("PUT", encoded_url, body=json.dumps({"group": new_val}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'test' == jdoc['default']
        assert 'test' == jdoc['value']
        assert new_val == jdoc['group']

        # Verify new value in GET endpoint
        conn.request("GET", encoded_url)
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert 'test' == jdoc['default']
        assert 'test' == jdoc['value']
        assert new_val == jdoc['group']

    def test_update_configuration_item_bulk(self, fledge_url):
        expected = {
            'item1': {'type': 'boolean', 'default': 'false', 'value': 'false', 'description': 'A Boolean check'},
            'item2': {'type': 'integer', 'description': 'An Integer check', 'default': '2', 'value': '1'},
            'item3': {'type': 'password', 'description': 'A password check', 'default': 'Fledge', 'value': "****"},
            'item4': {'type': 'string', 'description': 'A string check', 'default': 'fledge', 'value': 'new'},
            'item5': {'type': 'script', 'description': 'A script check', 'default': '', 'value': ''},
            'item6': {'type': 'string', 'description': 'A string check', 'default': 'test', 'value': 'test',
                      'group': 'Security'}
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
        actual = jdoc["categories"]
        assert 3 == len(actual)
        result = sorted(expected, key=lambda ex_element: sorted(ex_element.items())
                        ) == sorted(actual, key=lambda ac_element: sorted(ac_element.items()))
        assert result

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
        expected = {
            'item1': {'type': 'boolean', 'default': 'false', 'value': 'false', 'description': 'A Boolean check'},
            'item2': {'type': 'integer', 'description': 'An Integer check', 'default': '2', 'value': '1'},
            'item3': {'type': 'password', 'description': 'A password check', 'default': 'Fledge', 'value': "****"},
            'item4': {'type': 'string', 'description': 'A string check', 'default': 'fledge', 'value': 'fledge'},
            'item5': {'default': '', 'value': 'import logging\nfrom logging.handlers import SysLogHandler\n\n\ndef notify35(message):\n    logger = logging.getLogger(__name__)\n    logger.setLevel(level=logging.INFO)\n    handler = SysLogHandler(address=\'/dev/log\')\n    logger.addHandler(handler)\n\n    logger.info("notify35 called with {}".format(message))\n    print("Notification alert: " + str(message))\n', 'file': script_file_path, 'type': 'script', 'description': 'A script check'},
            'item6': {'type': 'string', 'description': 'A string check', 'default': 'test', 'value': 'test',
                      'group': 'Security'}
        }
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

    def test_list_configuration_with_list_name(self, fledge_url):
        category = "TEST #123"
        config_item1 = "info"
        config_item2 = "list-1"
        config_item3 = "list-2"
        config_item4 = "list-3"
        payload = {'key': category, 'description': 'Test description'}
        conf = {
            config_item1: {'type': 'boolean', 'description': 'A Boolean check', 'default': 'False', 'order': '1'},
            config_item2: {'type': 'list', 'description': 'A list of variables', 'listName': 'items',
                           'items': 'string', 'default': '{"items": ["a", "b"]}', 'displayName': 'ListName',
                           'order': '2'},
            config_item3: {'type': 'list', 'description': 'A list of variables', 'items': 'string',
                           'default': '["foo", "bar"]', 'displayName': 'Simple List', 'order': '3'},
            config_item4: {'type': 'list', 'description': 'A list of datapoints to read PLC registers definitions',
                           'items': 'object', 'listName': 'map-items', 'displayName': 'PLC Map',
                           'default': '{"map-items": [{"datapoint": "voltage", "register": "10", "type": "integer"}]}',
                           'properties': {
                               'datapoint': {'description': 'The datapoint name to create', 'displayName': 'Datapoint',
                                             'type': 'string', 'default': ''},
                               'register': {'description': 'The register number to read', 'displayName': 'Register',
                                            'type': 'integer', 'default': '0'},
                               'type': {'description': 'The data type to read', 'displayName': 'Data Type',
                                        'type': 'enumeration', 'options': ['integer', 'float'], 'default': 'integer'}}}
        }
        payload.update({'value': conf})
        conn = http.client.HTTPConnection(fledge_url)
        conn.request('POST', '/fledge/category', body=json.dumps(payload))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert category == jdoc['key']
        # Verify default and value KV pair for a config item
        assert conf[config_item2]['default'] == jdoc['value'][config_item2]['default']
        assert conf[config_item2]['default'] == jdoc['value'][config_item2]['value']

        assert conf[config_item3]['default'] == jdoc['value'][config_item3]['default']
        assert conf[config_item3]['default'] == jdoc['value'][config_item3]['value']

        assert conf[config_item4]['default'] == jdoc['value'][config_item4]['default']
        assert conf[config_item4]['default'] == jdoc['value'][config_item4]['value']

        # Merge category test scenario
        payload.update({'value': conf})
        conn = http.client.HTTPConnection(fledge_url)
        conn.request('POST', '/fledge/category', body=json.dumps(payload))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert category == jdoc['key']
        # Verify No change in default and value KV pair for a config item
        assert conf[config_item2]['default'] == jdoc['value'][config_item2]['default']
        assert conf[config_item2]['default'] == jdoc['value'][config_item2]['value']
        assert conf[config_item3]['default'] == jdoc['value'][config_item3]['default']
        assert conf[config_item3]['default'] == jdoc['value'][config_item3]['value']
        assert conf[config_item4]['default'] == jdoc['value'][config_item4]['default']
        assert conf[config_item4]['default'] == jdoc['value'][config_item4]['value']

        # Bulk update
        encoded_url = '/fledge/category/{}'.format(quote(category))
        new_value_for_config_item2 = '["a", "b", "c"]'
        # with single config item
        conn.request("PUT", encoded_url, body=json.dumps({config_item2: new_value_for_config_item2}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert json.dumps({conf[config_item2]['listName']: json.loads(new_value_for_config_item2)}
                          ) == jdoc[config_item2]['value']
        # with multiple config items
        new_value_for_config_item4 = ('[{"datapoint": "voltage", "register": "10", "type": "integer"}, '
                                      '{"datapoint": "pressure", "register": "75.4", "type": "float"}]')
        conn.request("PUT", encoded_url, body=json.dumps({config_item2: new_value_for_config_item2,
                                                          config_item4: new_value_for_config_item4}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert json.dumps({conf[config_item2]['listName']: json.loads(new_value_for_config_item2)}) == \
               jdoc[config_item2]['value']
        assert json.dumps({conf[config_item4]['listName']: json.loads(new_value_for_config_item4)}) == \
               jdoc[config_item4]['value']

        # Single update call
        new_value_for_config_item2 = '["a", "b", "c", "d"]'
        encoded_url = '/fledge/category/{}/{}'.format(quote(category), config_item2)
        conn.request("PUT", encoded_url, body=json.dumps({"value": new_value_for_config_item2}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert json.dumps({conf[config_item2]['listName']: json.loads(new_value_for_config_item2)}) == jdoc['value']

        new_value_for_config_item4 = '[{"datapoint": "pressure", "register": "75.4", "type": "float"}]'
        encoded_url = '/fledge/category/{}/{}'.format(quote(category), config_item4)
        conn.request("PUT", encoded_url, body=json.dumps({"value": new_value_for_config_item4}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert json.dumps({conf[config_item4]['listName']: json.loads(new_value_for_config_item4)}) == jdoc['value']

