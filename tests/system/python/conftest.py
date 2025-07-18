# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Configuration system/python/conftest.py
"""
import subprocess
import os
import sys
import fnmatch
import http.client
import json
import base64
import ssl
import shutil
from urllib.parse import quote
from pathlib import Path
import time
import pytest
from helpers import utils


__author__ = "Vaibhav Singhal"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

sys.path.append(os.path.join(os.path.dirname(__file__), 'helpers'))
sys.path.append(os.path.join(os.path.dirname(__file__)))


@pytest.fixture
def clean_setup_fledge_packages(package_build_version):
    # This  gives the path of directory where fledge is cloned. conftest_file < python < system < tests < ROOT
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
    SCRIPTS_DIR_ROOT = "{}/tests/system/python/scripts/package/".format(PROJECT_ROOT)

    try:
        subprocess.run(["cd {} && ./remove"
                       .format(SCRIPTS_DIR_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "remove package script failed!"

    try:
        subprocess.run(["cd {} && ./setup {}"
                       .format(SCRIPTS_DIR_ROOT, package_build_version)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "setup package script failed"


@pytest.fixture
def reset_and_start_fledge(storage_plugin, readings_plugin, authentication):
    """Fixture that kills fledge, reset database and starts fledge again
        storage_plugin: A fixture that specifies the storage plugin to be used in the tests.
        readings_plugin: A fixture that specifies the readings plugin to be used in the tests.
        authentication: A fixture that defines the authentication method to be used for the tests. By default 'optional'
    """
    assert os.environ.get('FLEDGE_ROOT') is not None

    subprocess.run(["$FLEDGE_ROOT/scripts/fledge kill"], shell=True, check=True)
    assert storage_plugin in ["sqlite", "postgres", "sqlitelb"]
    assert readings_plugin in ["Use main plugin", "sqlitememory", "sqlite", "postgres", "sqlitelb"]
    subprocess.run(
        ["echo $(jq -c --arg STORAGE_PLUGIN_VAL {} '.plugin.value=$STORAGE_PLUGIN_VAL' "
         "$FLEDGE_ROOT/data/etc/storage.json) > $FLEDGE_ROOT/data/etc/storage.json".format(storage_plugin)],
        shell=True, check=True)
    subprocess.run(
        ["echo $(jq -c --arg READINGS_PLUGIN_VAL \"{}\" '.readingPlugin.value=$READINGS_PLUGIN_VAL' "
         "$FLEDGE_ROOT/data/etc/storage.json) > $FLEDGE_ROOT/data/etc/storage.json".format(readings_plugin)],
        shell=True, check=True)
    if authentication == 'optional':
        subprocess.run(["sed -i \"s/'default': 'mandatory'/'default': 'optional'/g\" "
                        "$FLEDGE_ROOT/python/fledge/services/core/server.py"], shell=True, check=True)
    else:
        subprocess.run(["sed -i \"s/'default': 'optional'/'default': 'mandatory'/g\" "
                        "$FLEDGE_ROOT/python/fledge/services/core/server.py"], shell=True, check=True)
    subprocess.run(["echo 'YES\nYES' | $FLEDGE_ROOT/scripts/fledge reset"], shell=True, check=True)
    subprocess.run(["$FLEDGE_ROOT/scripts/fledge start"], shell=True)
    stat = subprocess.run(["$FLEDGE_ROOT/scripts/fledge status"], shell=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    assert "Fledge not running." not in stat.stderr.decode("utf-8")


def find(pattern, path):
    result = None
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result = os.path.join(root, name)
    return result


@pytest.fixture
def remove_data_file():
    """Fixture that removes any file from a given path"""

    def _remove_data_file(file_path=None):
        if os.path.exists(file_path):
            os.remove(file_path)

    return _remove_data_file


@pytest.fixture
def remove_directories():
    """Fixture that recursively removes any file and directories from a given path"""

    def _remove_directories(dir_path=None):
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path, ignore_errors=True)

    return _remove_directories


@pytest.fixture
def add_south():
    def _add_fledge_south(south_plugin, south_branch, fledge_url, service_name="play", config=None,
                          plugin_lang="python", use_pip_cache=True, start_service=True, plugin_discovery_name=None,
                          installation_type='make'):
        """Add south plugin and start the service by default"""

        plugin_discovery_name = south_plugin if plugin_discovery_name is None else plugin_discovery_name
        _config = config if config is not None else {}
        _enabled = "true" if start_service else "false"
        data = {"name": "{}".format(service_name), "type": "South", "plugin": "{}".format(plugin_discovery_name),
                "enabled": _enabled, "config": _config}

        conn = http.client.HTTPConnection(fledge_url)

        def clone_make_install():
            try:
                if plugin_lang == "python":
                    subprocess.run(
                        ["$FLEDGE_ROOT/tests/system/python/scripts/install_python_plugin {} south {} {}".format(
                            south_branch, south_plugin, use_pip_cache)], shell=True, check=True)
                else:
                    subprocess.run(["$FLEDGE_ROOT/tests/system/python/scripts/install_c_plugin {} south {}".format(
                        south_branch, south_plugin)], shell=True, check=True)
            except subprocess.CalledProcessError:
                assert False, "{} plugin installation failed".format(south_plugin)

        if installation_type == 'make':
            clone_make_install()
        elif installation_type == 'package':
            try:
                subprocess.run(["sudo {} install -y fledge-south-{}".format(pytest.PKG_MGR, south_plugin)], shell=True,
                               check=True)
            except subprocess.CalledProcessError:
                assert False, "{} package installation failed!".format(south_plugin)
        else:
            print("Skipped {} plugin installation. Installation mechanism is set to {}.".format(south_plugin,
                                                                                                installation_type))

        # Create south service
        conn.request("POST", '/fledge/service', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        assert service_name == retval["name"]
        return retval

    return _add_fledge_south


@pytest.fixture
def add_north():
    def _add_fledge_north(fledge_url, north_plugin, north_branch, installation_type='make', north_instance_name="play",
                          config=None, schedule_repeat_time=30, 
                          plugin_lang="python", use_pip_cache=True, enabled=True, plugin_discovery_name=None,
                          is_task=True):
        """Add north plugin and start the service/task by default"""

        if plugin_discovery_name is None:
            plugin_discovery_name = north_plugin
        _config = config if config is not None else {}
        _enabled = "true" if enabled else "false"

        conn = http.client.HTTPConnection(fledge_url)

        def clone_make_install():
            try:
                if plugin_lang == "python":
                    subprocess.run(
                        ["$FLEDGE_ROOT/tests/system/python/scripts/install_python_plugin {} north {} {}".format(
                            north_branch, north_plugin, use_pip_cache)], shell=True, check=True)
                else:
                    subprocess.run(["$FLEDGE_ROOT/tests/system/python/scripts/install_c_plugin {} north {}".format(
                        north_branch, north_plugin)], shell=True, check=True)
            except subprocess.CalledProcessError:
                assert False, "{} plugin installation failed".format(north_plugin)

        if installation_type == 'make':
            clone_make_install()
        elif installation_type == 'package':
            try:
                subprocess.run(["sudo {} install -y fledge-north-{}".format(pytest.PKG_MGR, north_plugin)], shell=True,
                               check=True)
            except subprocess.CalledProcessError:
                assert False, "{} package installation failed!".format(north_plugin)
        else:
            print("Skipped {} plugin installation. Installation mechanism is set to {}.".format(north_plugin,
                                                                                                installation_type))

        if is_task:
            # Create north task
            data = {"name": "{}".format(north_instance_name), "type": "north",
                    "plugin": "{}".format(plugin_discovery_name),
                    "schedule_enabled": _enabled, "schedule_repeat": "{}".format(schedule_repeat_time), "schedule_type": "3", "config": _config}
            print(data)
            conn.request("POST", '/fledge/scheduled/task', json.dumps(data))
        else:
            # Create north service
            data = {"name": "{}".format(north_instance_name), "type": "North",
                    "plugin": "{}".format(plugin_discovery_name),
                    "enabled": _enabled, "config": _config}
            print(data)
            conn.request("POST", '/fledge/service', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        retval = json.loads(r)
        assert north_instance_name == retval["name"]
        return retval

    return _add_fledge_north

@pytest.fixture
def add_service():
    def _add_service(fledge_url, service, service_branch, retries, installation_type = "make", service_name = "svc@123",
                     enabled = True):
        
        """ 
            Fixture to add Service and start the start service by default
            fledge_url: IP address or domain to access fledge
            service: Service to be installed
            service_branch: Branch of service to be installed
            retries: Number of tries for polling
            installation_type: Type of installation for service i.e. make or package
            service_name: Name that will be given to service to be installed
            enabled: Flag to enable or disable notification instance
        """
        
        # Check if the service is already installed installed
        retval = utils.get_request(fledge_url, "/fledge/service")
        for ele in retval["services"]:
            if ele["type"].lower() == service:
                return ele
        
        PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
        
        # Install Service
        def clone_make_install():
            try:
                subprocess.run(["{}/tests/system/python/scripts/install_c_service {} {}".format(
                    PROJECT_ROOT, service_branch, service)], shell=True, check=True)
            except subprocess.CalledProcessError:
                assert False, "{} service  installation failed".format(service)
                
        if installation_type == 'make':
            clone_make_install()
        elif installation_type == 'package':
            try:
                subprocess.run(["sudo {} install -y fledge-service-{}".format(pytest.PKG_MGR, service)], shell=True,
                            check=True)
            except subprocess.CalledProcessError:
                assert False, "{} package installation failed!".format(service)
        else:
            return("Skipped {} service installation. Installation mechanism is set to {}.".format(service, installation_type))
        
        # Add Service
        data = {"name": "{}".format(service_name), "type": "{}".format(service), "enabled": enabled}
        retval = utils.post_request(fledge_url, "/fledge/service", data)
        assert service_name == retval["name"]
        return retval
        
    return _add_service

@pytest.fixture
def add_notification_instance():
    def _add_notification_instance(fledge_url, delivery_plugin, delivery_branch , rule_config={}, delivery_config={}, 
                                   rule_plugin="Threshold", rule_branch=None, rule_plugin_discovery_name=None, 
                                   delivery_plugin_discovery_name=None, installation_type='make', notification_type="one shot",
                                   notification_instance_name="noti@123", retrigger_time=30, enabled=True):
        """
            Fixture to add Service instance and start the instance by default
            fledge_url: IP address or domain to access fledge
            delivery_plugin: Notify or Delivery plugin to be installed
            delivery_branch: Branch of Notify or Delivery plugin to be installed
            rule_config: Configuration of Rule plugin
            delivery_config: Configuration of Delivery plugin
            rule_plugin: Rule plugin to be installed, by default Threshold and DataAvailability plugin is installed 
            rule_branch: Branch of Rule plugin to be installed
            rule_plugin_discovery_name: Name to identify the Rule Plugin after installation 
            delivery_plugin_discovery_name: Name to identify the Delivery Plugin after installation 
            installation_type: Type of installation for plugins i.e. make or package
            notification_type: Type of notification to be triggered i.e. one_shot, retriggered, toggle
            notification_instance_name: Name that will be given to notification instance to be created
            retrigger_time: Interval between retriggered notifications
            enabled: Flag to enable or disable notification instance
        """
        PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
        
        if rule_plugin_discovery_name is None:
            rule_plugin_discovery_name = rule_plugin
            
        if delivery_plugin_discovery_name is None:
            delivery_plugin_discovery_name = delivery_plugin

        def clone_make_install(plugin_branch, plugin_type, plugin):
            try:
                subprocess.run(["{}/tests/system/python/scripts/install_c_plugin {} {} {}".format(
                    PROJECT_ROOT, plugin_branch, plugin_type, plugin)], shell=True, check=True)
            except subprocess.CalledProcessError:
                assert False, "{} plugin installation failed".format(plugin)

        if installation_type == 'make':
            # Install Rule Plugin if it is not Threshold or DataAvailability
            if rule_plugin not in  ("Threshold","DataAvailability"):
                clone_make_install(rule_branch, "rule", rule_plugin)
            
            clone_make_install(delivery_branch, "notify", delivery_plugin)
            
        elif installation_type == 'package':
            try:
                if rule_plugin not in ["Threshold", "DataAvailability"]:
                    subprocess.run(["sudo {} install -y fledge-rule-{}".format(pytest.PKG_MGR, rule_plugin)], shell=True,
                               check=True)
                    
            except subprocess.CalledProcessError:
                assert False, "Package installation of {} failed!".format(rule_plugin)
                
            try :
                subprocess.run(["sudo {} install -y fledge-notify-{}".format(pytest.PKG_MGR, delivery_plugin)], shell=True,
                               check=True)
                
            except subprocess.CalledProcessError:
                assert False, "Package installation of {} failed!".format(delivery_plugin)
        else:
            return("Skipped {} and {} plugin installation. Installation mechanism is set to {}.".format(rule_plugin, delivery_plugin,
                                                                                                installation_type))

        data = {
                "name": notification_instance_name,
                "description": "{} notification instance".format(notification_instance_name),
                "rule_config": rule_config,
                "rule": rule_plugin_discovery_name,
                "delivery_config": delivery_config,
                "channel": delivery_plugin_discovery_name,
                "notification_type": notification_type,
                "enabled": enabled, 
                "retrigger_time": "{}".format(retrigger_time),
                }
        
        retval = utils.post_request(fledge_url, "/fledge/notification", data)
        assert "Notification {} created successfully".format(notification_instance_name) == retval["result"]
        return retval
    
    return _add_notification_instance

@pytest.fixture
def start_north_pi_v2():
    def _start_north_pi_server_c(fledge_url, pi_host, pi_port, pi_token, north_plugin="OMF",
                                 taskname="NorthReadingsToPI", start_task=True, naming_scheme="Backward compatibility",
                                 pi_use_legacy="true"):
        """Start north task"""

        _enabled = "true" if start_task else "false"
        conn = http.client.HTTPConnection(fledge_url)
        data = {"name": taskname,
                "plugin": "{}".format(north_plugin),
                "type": "north",
                "schedule_type": 3,
                "schedule_day": 0,
                "schedule_time": 0,
                "schedule_repeat": 30,
                "schedule_enabled": _enabled,
                "config": {"PIServerEndpoint": {"value": "Connector Relay"},
                           "producerToken": {"value": pi_token},
                           "ServerHostname": {"value": pi_host},
                           "ServerPort": {"value": str(pi_port)},
                           "NamingScheme": {"value": naming_scheme},
                           "Legacy": {"value": pi_use_legacy}
                           }
                }
        conn.request("POST", '/fledge/scheduled/task', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        retval = r.read().decode()
        return retval

    return _start_north_pi_server_c


@pytest.fixture
def start_north_task_omf_web_api():
    def _start_north_task_omf_web_api(fledge_url, pi_host, pi_port, pi_db="Dianomic", auth_method='basic',
                                      pi_user=None, pi_pwd=None, north_plugin="OMF",
                                      taskname="NorthReadingsToPI_WebAPI", start_task=True,
                                      naming_scheme="Backward compatibility",
                                      default_af_location="fledge/room1/machine1",
                                      pi_use_legacy="true"):
        """Start north task"""

        _enabled = True if start_task else False
        conn = http.client.HTTPConnection(fledge_url)
        data = {"name": taskname,
                "plugin": "{}".format(north_plugin),
                "type": "north",
                "schedule_type": 3,
                "schedule_day": 0,
                "schedule_time": 0,
                "schedule_repeat": 10,
                "schedule_enabled": _enabled,
                "config": {"PIServerEndpoint": {"value": "PI Web API"},
                           "PIWebAPIAuthenticationMethod": {"value": auth_method},
                           "PIWebAPIUserId": {"value": pi_user},
                           "PIWebAPIPassword": {"value": pi_pwd},
                           "ServerHostname": {"value": pi_host},
                           "ServerPort": {"value": str(pi_port)},
                           "compression": {"value": "true"},
                           "DefaultAFLocation": {"value": default_af_location},
                           "NamingScheme": {"value": naming_scheme},
                           "Legacy": {"value": pi_use_legacy}
                           }
                }

        conn.request("POST", '/fledge/scheduled/task', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        retval = r.read().decode()
        return retval

    return _start_north_task_omf_web_api


@pytest.fixture
def start_north_omf_as_a_service():
    def _start_north_omf_as_a_service(fledge_url, pi_host, pi_port, pi_db="Dianomic", auth_method='basic',
                                      pi_user=None, pi_pwd=None, north_plugin="OMF",
                                      service_name="NorthReadingsToPI_WebAPI", start=True,
                                      naming_scheme="Backward compatibility",
                                      default_af_location="fledge/room1/machine1",
                                      pi_use_legacy="true"):
        """Start north service"""

        _enabled = True if start else False
        conn = http.client.HTTPConnection(fledge_url)
        data = {"name": service_name,
                "plugin": "{}".format(north_plugin),
                "enabled": _enabled,
                "type": "north",
                "config": {"PIServerEndpoint": {"value": "PI Web API"},
                           "PIWebAPIAuthenticationMethod": {"value": auth_method},
                           "PIWebAPIUserId": {"value": pi_user},
                           "PIWebAPIPassword": {"value": pi_pwd},
                           "ServerHostname": {"value": pi_host},
                           "ServerPort": {"value": str(pi_port)},
                           "compression": {"value": "true"},
                           "DefaultAFLocation": {"value": default_af_location},
                           "NamingScheme": {"value": naming_scheme},
                           "Legacy": {"value": pi_use_legacy}
                           }
                }

        conn.request("POST", '/fledge/service', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        retval = json.loads(r.read().decode())
        return retval

    return _start_north_omf_as_a_service


start_north_pi_server_c = start_north_pi_v2
start_north_pi_server_c_web_api = start_north_pi_v2_web_api = start_north_task_omf_web_api


@pytest.fixture
def read_data_from_pi():
    def _read_data_from_pi(host, admin, password, pi_database, asset, sensor):
        """ This method reads data from pi web api """

        # List of pi databases
        dbs = None
        # PI logical grouping of attributes and child elements
        elements = None
        # List of elements
        url_elements_list = None
        # Element's recorded data url
        url_recorded_data = None
        # Resources in the PI Web API are addressed by WebID, parameter used for deletion of element
        web_id = None

        username_password = "{}:{}".format(admin, password)
        username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
        headers = {'Authorization': 'Basic %s' % username_password_b64}

        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            ctx.options |= ssl.PROTOCOL_TLSv1_1
            # With ssl.CERT_NONE as verify_mode, validation errors such as untrusted or expired cert
            # are ignored and do not abort the TLS/SSL handshake.
            ctx.verify_mode = ssl.CERT_NONE
            conn = http.client.HTTPSConnection(host, context=ctx)
            conn.request("GET", '/piwebapi/assetservers', headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            dbs = r["Items"][0]["Links"]["Databases"]

            if dbs is not None:
                conn.request("GET", dbs, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
                for el in r["Items"]:
                    if el["Name"] == pi_database:
                        elements = el["Links"]["Elements"]

            if elements is not None:
                conn.request("GET", elements, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
                url_elements_list = r["Items"][0]["Links"]["Elements"]

            if url_elements_list is not None:
                conn.request("GET", url_elements_list, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
                items = r["Items"]
                for el in items:
                    if el["Name"] == asset:
                        url_recorded_data = el["Links"]["RecordedData"]
                        web_id = el["WebId"]

            _data_pi = {}
            if url_recorded_data is not None:
                conn.request("GET", url_recorded_data, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
                _items = r["Items"]
                for el in _items:
                    _recoded_value_list = []
                    for _head in sensor:
                        if el["Name"] == _head:
                            elx = el["Items"]
                            for _el in elx:
                                _recoded_value_list.append(_el["Value"])
                            _data_pi[_head] = _recoded_value_list

                # Delete recorded elements
                conn.request("DELETE", '/piwebapi/elements/{}'.format(web_id), headers=headers)
                res = conn.getresponse()
                res.read()

                return _data_pi
        except (KeyError, IndexError, Exception):
            return None

    return _read_data_from_pi


@pytest.fixture
def clear_pi_system_through_pi_web_api():
    PROJECT_ROOT = Path(__file__).absolute().parent.parent.parent.parent
    sys.path.append('{}/tests/system/common'.format(PROJECT_ROOT))

    from clean_pi_system import clear_pi_system_pi_web_api

    return clear_pi_system_pi_web_api

@pytest.fixture
def verify_hierarchy_and_get_datapoints_from_pi_web_api():
    def _verify_hierarchy_and_get_datapoints_from_pi_web_api(host, admin, password, pi_database, af_hierarchy_list, asset, sensor):
        """ This method verifies hierarchy created in pi web api is correctly """
    
        username_password = "{}:{}".format(admin, password)
        username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
        headers = {'Authorization': 'Basic %s' % username_password_b64}
        AF_HIERARCHY_LIST=af_hierarchy_list.split('/')[1:]
        AF_HIERARCHY_COUNT=len(AF_HIERARCHY_LIST)
        
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            ctx.options |= ssl.PROTOCOL_TLSv1_1
            # With ssl.CERT_NONE as verify_mode, validation errors such as untrusted or expired cert
            # are ignored and do not abort the TLS/SSL handshake.
            ctx.verify_mode = ssl.CERT_NONE
            conn = http.client.HTTPSConnection(host, context=ctx)
            conn = http.client.HTTPSConnection(host, context=ctx)
            conn.request("GET", '/piwebapi/assetservers', headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            dbs_url= r['Items'][0]['Links']['Databases']
            print(dbs_url)
            if dbs_url is not None:
                conn.request("GET", dbs_url, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
                items = r['Items']
                CHECK_DATABASE_EXISTS = list(filter(lambda items: items['Name'] == pi_database, items))[0]
                
                if len(CHECK_DATABASE_EXISTS) > 0:
                    elements_url = CHECK_DATABASE_EXISTS['Links']['Elements']
                else:
                    raise Exception('Database not exist')
                
                if elements_url is not None:
                    conn.request("GET", elements_url, headers=headers)
                    res = conn.getresponse()
                    r = json.loads(res.read().decode())
                    items = r['Items']
                    
                    CHECK_AF_ELEMENT_EXISTS = list(filter(lambda items: items['Name'] == AF_HIERARCHY_LIST[0], items))[0]
                    if len(CHECK_AF_ELEMENT_EXISTS) != 0:
                        
                        counter =  0
                        while counter < AF_HIERARCHY_COUNT:
                            if CHECK_AF_ELEMENT_EXISTS['Name'] == AF_HIERARCHY_LIST[counter]:
                                counter+=1
                                elements_url = CHECK_AF_ELEMENT_EXISTS['Links']['Elements']
                                conn.request("GET", elements_url, headers=headers)
                                res = conn.getresponse()
                                CHECK_AF_ELEMENT_EXISTS = json.loads(res.read().decode())['Items'][0]
                            else:
                                raise Exception("AF Heirarchy is incorrect")
                            
                        record = dict()
                        if CHECK_AF_ELEMENT_EXISTS['Name'] == asset:
                            record_url = CHECK_AF_ELEMENT_EXISTS['Links']['RecordedData']
                            get_record_url = quote("{}?limit=10000".format(record_url), safe='?,=&/.:')
                            print(get_record_url)
                            conn.request("GET", get_record_url, headers=headers)
                            res = conn.getresponse()
                            items = json.loads(res.read().decode())['Items']
                            no_of_datapoint_in_pi_server = len(items)
                            Item_matched = False
                            count = 0
                            if no_of_datapoint_in_pi_server == 0:
                                raise "Data points are not created in PI Server"
                            else:
                                for item in items:
                                    count += 1
                                    if item['Name'] in sensor:
                                        print(item['Name'])
                                        record[item['Name']] = list(map(lambda val: val['Value'], filter(lambda ele: isinstance(ele['Value'], int) or isinstance(ele['Value'], float) , item['Items'])))
                                        Item_matched = True
                                    elif count == no_of_datapoint_in_pi_server and Item_matched == False:
                                        raise "Required Data points is not Present --> {}".format(sensor)
                        else:
                            raise "Asset does not exist, Although Hierarchy is correct"
                        
                        return(record)
                            
                    else:
                        raise Exception("AF Root not exists")
                else:
                    raise Exception("Elements URL not found")
            else:
                raise Exception("DataBase URL not found")
                
            
        except (KeyError, IndexError, Exception) as ex:
            print("Failed to read data due to {}".format(ex))
            return None
        
    return(_verify_hierarchy_and_get_datapoints_from_pi_web_api)

@pytest.fixture
def read_data_from_pi_web_api():
    def _read_data_from_pi_web_api(host, admin, password, pi_database, af_hierarchy_list, asset, sensor):
        """ This method reads data from pi web api """

        username_password = "{}:{}".format(admin, password)
        username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
        headers = {'Authorization': 'Basic %s' % username_password_b64}

        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            ctx.options |= ssl.PROTOCOL_TLSv1_1
            # With ssl.CERT_NONE as verify_mode, validation errors such as untrusted or expired cert
            # are ignored and do not abort the TLS/SSL handshake.
            ctx.verify_mode = ssl.CERT_NONE
            conn = http.client.HTTPSConnection(host, context=ctx)
            conn.request("GET", '/piwebapi/dataservers', headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            points= r["Items"][0]['Links']["Points"]
            
            if points is not None:
                conn.request("GET", points, headers=headers)
                res = conn.getresponse()
                r=json.loads(res.read().decode())
                data = r["Items"]
                if data is not None:
                    value = None
                    if sensor == '':
                        search_string = asset
                    else:
                        search_string = "{}.{}".format(asset, sensor)
                    for el in data:
                        if search_string in el["Name"]:
                            value_url = el["Links"]["Value"]
                            if value_url is not None:
                                conn.request("GET", value_url, headers=headers)
                                res = conn.getresponse()
                                r = json.loads(res.read().decode())
                                value = r["Value"]
                    if not value:
                        print("Could not find the latest reading of asset ->{}. sensor->{}".format(asset,
                                  sensor))
                        return value
                    else:
                        print("The latest value of asset->{}.sensor->{} is {}".format(asset, sensor, value))
                        return(value)
                else:
                    print("Data inside points not found.")
                    return None     
            else:
                print("Could not find the points.")
                return None

        except (KeyError, IndexError, Exception) as ex:
            print("Failed to read data due to {}".format(ex))
            return None

    return _read_data_from_pi_web_api


@pytest.fixture
def read_data_from_pi_asset_server():
    def _read_data_from_pi_asset_server(host, admin, password, pi_database, asset, sensor, af_hierarchy_list=['fledge', 'room1', 'machine1']):
        """This method reads data from PI Web API asset server"""

        # Initialize variables
        dbs = None
        # PI logical grouping of attributes and child elements
        elements = None
        # List of elements
        url_elements_list = None
        # Element's recorded data url
        url_recorded_data = None
        # Resources in the PI Web API are addressed by WebID, parameter used for deletion of element
        web_id = None
        # URL of source datapoint
        source_link = None

        # Create the basic authorization header
        username_password = "{}:{}".format(admin, password)
        username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
        headers = {'Authorization': 'Basic %s' % username_password_b64}

        try:
            # Establish a connection to the PI Asset Server
            conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
            conn.request("GET", '/piwebapi/assetservers', headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            dbs = r["Items"][0]["Links"]["Databases"]

            if dbs is not None:
                conn.request("GET", dbs, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
                for el in r["Items"]:
                    if el["Name"] == pi_database:
                        url_elements_list = el["Links"]["Elements"]
            else:
                print("Unable to find Databases")
                return None
            
            # This block is for iteration when we have multi-level hierarchy.
            # For example, if we have DefaultAFLocation as "foglamp/room1/machine1" then
            # it will recursively find elements of "foglamp" and then "room1".
            # And next block is for finding element of "machine1".
            
            # Iterate through AF hierarchy list
            af_level_count = 0
            for level in af_hierarchy_list:
                if url_elements_list is not None:
                    conn.request("GET", url_elements_list, headers=headers)
                    res = conn.getresponse()
                    r = json.loads(res.read().decode())
                    for el in r["Items"]:
                        if el["Name"] == af_hierarchy_list[af_level_count]:
                            url_elements_list = el["Links"]["Elements"]
                            if af_level_count == 0:
                                web_id_root = el["WebId"]
                            af_level_count += 1

            if url_elements_list is not None:
                conn.request("GET", url_elements_list, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
                items = r["Items"]
                for el in items:
                    if asset in el["Name"]:
                        url_recorded_data = el["Links"]["RecordedData"]
                        web_id = el["WebId"]
            
            _data_pi = {}
            if url_recorded_data is not None:
                conn.request("GET", url_recorded_data, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
                _items = r["Items"]
                
                for el in _items:
                    _recoded_value_list = list()
                    if len(sensor) == 1 and el["Name"].endswith(asset):
                        for itm in el["Items"]:
                            _recoded_value_list.append(itm["Value"])
                        _data_pi[sensor.pop()] = _recoded_value_list
                    else:
                        for _head in sensor:
                            if el["Name"].endswith(f"{asset}.{_head}"):
                                for itm in el["Items"]:
                                    _recoded_value_list.append(itm["Value"])
                                _data_pi[_head] = _recoded_value_list

            return _data_pi

        except (KeyError, IndexError, Exception) as ex:
            print("Failed to read data due to {}".format(ex))
            print(ex.__traceback__.tb_lineno)
            return None

    return _read_data_from_pi_asset_server


@pytest.fixture
def add_filter():
    def _add_filter(filter_plugin, filter_plugin_branch, filter_name, filter_config, fledge_url, filter_user_svc_task,
                    installation_type='make', only_installation=False):
        """

        :param filter_plugin: filter plugin `fledge-filter-?`
        :param filter_plugin_branch:
        :param filter_name: name of the filter with which it will be added to pipeline
        :param filter_config:
        :param fledge_url:
        :param filter_user_svc_task: south service or north task instance name
        """

        if installation_type == 'make':
            try:
                subprocess.run(["$FLEDGE_ROOT/tests/system/python/scripts/install_c_plugin {} filter {}".format(
                    filter_plugin_branch, filter_plugin)], shell=True, check=True)
            except subprocess.CalledProcessError:
                assert False, "{} filter plugin installation failed".format(filter_plugin)
        elif installation_type == 'package':
            try:
                subprocess.run(["sudo {} install -y fledge-filter-{}".format(pytest.PKG_MGR, filter_plugin)],
                               shell=True, check=True)
            except subprocess.CalledProcessError:
                assert False, "{} package installation failed!".format(filter_plugin)
        else:
            print("Skipped {} plugin installation. Installation mechanism is set to {}.".format(filter_plugin,
                                                                                                installation_type))

        if only_installation:
            return

        data = {"name": "{}".format(filter_name), "plugin": "{}".format(filter_plugin), "filter_config": filter_config}
        conn = http.client.HTTPConnection(fledge_url)

        conn.request("POST", '/fledge/filter', json.dumps(data))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert filter_name == jdoc["filter"]

        uri = "{}/pipeline?allow_duplicates=true&append_filter=true".format(quote(filter_user_svc_task))
        filters_in_pipeline = [filter_name]
        conn.request("PUT", '/fledge/filter/' + uri, json.dumps({"pipeline": filters_in_pipeline}))
        r = conn.getresponse()
        assert 200 == r.status
        res = r.read().decode()
        jdoc = json.loads(res)
        # Asset newly added filter exist in request's response
        assert filter_name in jdoc["result"]
        return jdoc

    return _add_filter


@pytest.fixture
def enable_schedule():
    def _enable_sch(fledge_url, sch_name):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/schedule/enable', json.dumps({"schedule_name": sch_name}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "scheduleId" in jdoc
        return jdoc

    return _enable_sch


@pytest.fixture
def disable_schedule():
    def _disable_sch(fledge_url, sch_name):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("PUT", '/fledge/schedule/disable', json.dumps({"schedule_name": sch_name}))
        r = conn.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert jdoc["status"]
        return jdoc

    return _disable_sch


def pytest_addoption(parser):
    parser.addoption("--storage-plugin", action="store", default="sqlite",
                     help="Database plugin to use for tests")
    parser.addoption("--readings-plugin", action="store", default="Use main plugin",
                     help="Readings plugin to use for tests")
    parser.addoption("--fledge-url", action="store", default="localhost:8081",
                     help="Fledge client api url")
    parser.addoption("--use-pip-cache", action="store", default=False,
                     help="use pip cache is requirement is available")
    parser.addoption("--wait-time", action="store", default=5, type=int,
                     help="Generic wait time between processes to run")
    parser.addoption("--wait-fix", action="store", default=0, type=int,
                     help="Extra wait time required for process to run")
    parser.addoption("--retries", action="store", default=3, type=int,
                     help="Number of tries for polling")
    # TODO: Temporary fixture, to be used with value False for environments where PI Web API is not stable
    parser.addoption("--skip-verify-north-interface", action="store_false",
                     help="Verify data from external north system api")

    parser.addoption("--remote-user", action="store", default="ubuntu",
                     help="Username on remote machine where Fledge will run")
    parser.addoption("--remote-ip", action="store", default="127.0.0.1",
                     help="IP of remote machine where Fledge will run")
    parser.addoption("--key-path", action="store", default="~/.ssh/id_rsa.pub",
                     help="Path of key file used for authentication to remote machine")
    parser.addoption("--remote-fledge-path", action="store",
                     help="Path on the remote machine where Fledge is clone and built")

    # South/North Args
    parser.addoption("--south-branch", action="store", default="develop",
                     help="south branch name")
    parser.addoption("--north-branch", action="store", default="develop",
                     help="north branch name")
    parser.addoption("--south-service-name", action="store", default="southSvc #1",
                     help="Name of the South Service")
    parser.addoption("--asset-name", action="store", default="SystemTest",
                     help="Name of asset")
    parser.addoption("--num-assets", action="store", default=300, type=int, 
                     help="Total number of assets that need to be created")
    parser.addoption("--north-historian", action="store", default="EdgeDataStore",
                     help="Name of the North Historian to which the data will be sent")
    
    # Filter Args
    parser.addoption("--filter-branch", action="store", default="develop", help="Filter plugin repo branch")
    parser.addoption("--filter-name", action="store", default="Meta #1", help="Filter name to be added to pipeline")

    # External Services Arg fledge-service-* e.g. fledge-service-notification
    parser.addoption("--service-branch", action="store", default="develop",
                     help="service branch name")
    # Notify Arg
    parser.addoption("--notify-branch", action="store", default="develop", help="Notify plugin repo branch")

    # PI Config
    parser.addoption("--pi-host", action="store", default="pi-server",
                     help="PI Server Host Name/IP")
    parser.addoption("--pi-port", action="store", default="5460", type=int,
                     help="PI Server Port")
    parser.addoption("--pi-db", action="store", default="pi-server-db",
                     help="PI Server database")
    parser.addoption("--pi-admin", action="store", default="pi-server-uid",
                     help="PI Server user login")
    parser.addoption("--pi-passwd", action="store", default="pi-server-pwd",
                     help="PI Server user login password")
    parser.addoption("--pi-token", action="store", default="omf_north_0001",
                     help="OMF Producer Token")
    parser.addoption("--pi-use-legacy", action="store", default="true",
                     help="Set false to override the default plugin behaviour i.e. for OMF version >=1.2.x to send linked data types.")
    
    # OCS Config
    parser.addoption("--ocs-tenant", action="store", default="ocs_tenant_id",
                     help="Tenant id of OCS")
    parser.addoption("--ocs-client-id", action="store", default="ocs_client_id",
                     help="Client id of OCS account")
    parser.addoption("--ocs-client-secret", action="store", default="ocs_client_secret",
                     help="Client Secret of OCS account")
    parser.addoption("--ocs-namespace", action="store", default="ocs_namespace_0001",
                     help="OCS namespace where the information are stored")
    parser.addoption("--ocs-token", action="store", default="ocs_north_0001",
                     help="Token of OCS account")

    # Kafka Config
    parser.addoption("--kafka-host", action="store", default="localhost",
                     help="Kafka Server Host Name/IP")
    parser.addoption("--kafka-port", action="store", default="9092", type=int,
                     help="Kafka Server Port")
    parser.addoption("--kafka-topic", action="store", default="Fledge", help="Kafka topic")
    parser.addoption("--kafka-rest-port", action="store", default="8082", help="Kafka Rest Proxy Port")

    # Modbus Config
    parser.addoption("--modbus-host", action="store", default="localhost", help="Modbus simulator host")
    parser.addoption("--modbus-port", action="store", default="502", type=int, help="Modbus simulator port")
    parser.addoption("--modbus-serial-port", action="store", default="/dev/ttyS1", help="Modbus serial port")
    parser.addoption("--modbus-baudrate", action="store", default="9600", type=int, help="Serial port baudrate")

    # Packages
    parser.addoption("--package-build-version", action="store", default="nightly",
                     help="Package build version for http://archives.fledge-iot.org")
    parser.addoption("--package-build-list", action="store", default="p0",
                     help="Package to build as per key defined in tests/system/python/packages/data/package_list.json and comma separated values are accepted if more than one to build with")
    parser.addoption("--package-build-source-list", action="store", default="false",
                     help="Package to build from apt/yum sources list")
    parser.addoption("--exclude-packages-list", action="store", default="None",
                     help="Packages to be excluded from test e.g. --exclude-packages-list=fledge-south-sinusoid,fledge-filter-log")

    # Config required for testing fledge under impaired network.

    parser.addoption("--south-service-wait-time", action="store", type=int, default=20,
                     help="The time in seconds before which the south service should keep  on"
                          "sending data. After this time the south service will shutdown.")

    parser.addoption("--north-catch-up-time", action="store", type=int, default=30,
                     help="The time in seconds we will allow the north task /service"
                          " to keep on running "
                          "after switching off the south service.")

    parser.addoption('--throttled-network-config', action='store', type=json.loads,
                     help=   "Give config '{'rate_limit': '100',"
                             "            'packet_delay': '50',"
                             "            'interface': 'eth0'}' "
                             "for causing a delay of 50 milliseconds "
                             "and rate restriction of 100 kbps on interface eth0.")

    parser.addoption("--start-north-as-service", action="store", type=bool, default=True,
                     help="Whether start the north as a service.")

    # Fogbench Config
    parser.addoption("--fogbench-host", action="store", default="localhost",
                     help="FogBench Destination Host Address")
                     
    parser.addoption("--fogbench-port", action="store", default="5683", type=int,
                     help="FogBench Destination Port")
    
    # Azure-IoT Config
    parser.addoption("--azure-host", action="store", default="azure-server",
                     help="Azure-IoT Host Name")
    
    parser.addoption("--azure-device", action="store", default="azure-iot-device",
                     help="Azure-IoT Device ID")
    
    parser.addoption("--azure-key", action="store", default="azure-iot-key",
                     help="Azure-IoT SharedAccess key")
    
    parser.addoption("--azure-storage-account-url", action="store", default="azure-storage-account-url",
                     help="Azure Storage Account URL")
    
    parser.addoption("--azure-storage-account-key", action="store", default="azure-storage-account-key",
                     help="Azure Storage Account Access Key")
    
    parser.addoption("--azure-storage-container", action="store", default="azure_storage_container",
                     help="Container Name in Azure where data is stored")
    
    parser.addoption("--run-time", action="store", default="60",
                    help="The number of minute for which a test should run")

@pytest.fixture
def num_assets(request):
    return request.config.getoption("--num-assets")
    
@pytest.fixture
def storage_plugin(request):
    return request.config.getoption("--storage-plugin")


@pytest.fixture
def readings_plugin(request):
    return request.config.getoption("--readings-plugin")


@pytest.fixture
def remote_user(request):
    return request.config.getoption("--remote-user")


@pytest.fixture
def remote_ip(request):
    return request.config.getoption("--remote-ip")


@pytest.fixture
def key_path(request):
    return request.config.getoption("--key-path")


@pytest.fixture
def remote_fledge_path(request):
    return request.config.getoption("--remote-fledge-path")


@pytest.fixture
def skip_verify_north_interface(request):
    return not request.config.getoption("--skip-verify-north-interface")


@pytest.fixture
def south_branch(request):
    return request.config.getoption("--south-branch")


@pytest.fixture
def north_branch(request):
    return request.config.getoption("--north-branch")


@pytest.fixture
def service_branch(request):
    return request.config.getoption("--service-branch")


@pytest.fixture
def filter_branch(request):
    return request.config.getoption("--filter-branch")


@pytest.fixture
def notify_branch(request):
    return request.config.getoption("--notify-branch")


@pytest.fixture
def use_pip_cache(request):
    return request.config.getoption("--use-pip-cache")


@pytest.fixture
def filter_name(request):
    return request.config.getoption("--filter-name")


@pytest.fixture
def south_service_name(request):
    return request.config.getoption("--south-service-name")


@pytest.fixture
def asset_name(request):
    return request.config.getoption("--asset-name")


@pytest.fixture
def fledge_url(request):
    return request.config.getoption("--fledge-url")

@pytest.fixture
def authentication(request):
    return "optional"

@pytest.fixture
def wait_time(request):
    return request.config.getoption("--wait-time")

@pytest.fixture
def wait_fix(request):
    return request.config.getoption("--wait-fix")
    
@pytest.fixture
def retries(request):
    return request.config.getoption("--retries")

@pytest.fixture
def north_historian(request):
    return request.config.getoption("--north-historian")

@pytest.fixture
def pi_host(request):
    return request.config.getoption("--pi-host")


@pytest.fixture
def pi_port(request):
    return request.config.getoption("--pi-port")


@pytest.fixture
def pi_db(request):
    return request.config.getoption("--pi-db")


@pytest.fixture
def pi_admin(request):
    return request.config.getoption("--pi-admin")


@pytest.fixture
def pi_passwd(request):
    return request.config.getoption("--pi-passwd")


@pytest.fixture
def pi_token(request):
    return request.config.getoption("--pi-token")


@pytest.fixture
def pi_use_legacy(request):
    return request.config.getoption("--pi-use-legacy")


@pytest.fixture
def ocs_tenant(request):
    return request.config.getoption("--ocs-tenant")


@pytest.fixture
def ocs_client_id(request):
    return request.config.getoption("--ocs-client-id")


@pytest.fixture
def ocs_client_secret(request):
    return request.config.getoption("--ocs-client-secret")


@pytest.fixture
def ocs_namespace(request):
    return request.config.getoption("--ocs-namespace")


@pytest.fixture
def ocs_token(request):
    return request.config.getoption("--ocs-token")


@pytest.fixture
def kafka_host(request):
    return request.config.getoption("--kafka-host")


@pytest.fixture
def kafka_port(request):
    return request.config.getoption("--kafka-port")


@pytest.fixture
def kafka_topic(request):
    return request.config.getoption("--kafka-topic")


@pytest.fixture
def kafka_rest_port(request):
    return request.config.getoption("--kafka-rest-port")


@pytest.fixture
def modbus_host(request):
    return request.config.getoption("--modbus-host")


@pytest.fixture
def modbus_port(request):
    return request.config.getoption("--modbus-port")


@pytest.fixture
def modbus_serial_port(request):
    return request.config.getoption("--modbus-serial-port")


@pytest.fixture
def modbus_baudrate(request):
    return request.config.getoption("--modbus-baudrate")


@pytest.fixture
def package_build_version(request):
    return request.config.getoption("--package-build-version")


@pytest.fixture
def package_build_list(request):
    return request.config.getoption("--package-build-list")


@pytest.fixture
def package_build_source_list(request):
    return request.config.getoption("--package-build-source-list")


@pytest.fixture
def exclude_packages_list(request):
    return request.config.getoption("--exclude-packages-list")


def pytest_itemcollected(item):
    par = item.parent.obj
    node = item.obj
    pref = par.__doc__.strip() if par.__doc__ else par.__class__.__name__
    suf = node.__doc__.strip() if node.__doc__ else node.__name__
    if pref or suf:
        item._nodeid = ' '.join((pref, suf))


# Parameters required for testing Fledge under an impaired or noisy network.
@pytest.fixture
def south_service_wait_time(request):
    return request.config.getoption("--south-service-wait-time")


@pytest.fixture
def north_catch_up_time(request):
    return request.config.getoption("--north-catch-up-time")


@pytest.fixture
def throttled_network_config(request):
    return request.config.getoption("--throttled-network-config")


@pytest.fixture
def start_north_as_service(request):
    return request.config.getoption("--start-north-as-service")


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


def pytest_configure():
    pytest.OS_PLATFORM_DETAILS = read_os_release()
    pytest.IS_REDHAT = is_redhat_based()
    pytest.PKG_MGR = 'yum' if pytest.IS_REDHAT else 'apt'


def restart_and_wait_for_fledge(fledge_url, wait_time, auth_token=None):
    """ Restarts the Fledge service and waits until it becomes responsive

    Args:
        fledge_url (str): base fledge url
        wait_time (int): Seconds between retries
        auth_token (str): Authorization Token (Optional)
    Raises:
        AssertionError: If Fledge failed to restart

    Returns:
        JSON Document
    """
    from contextlib import closing
    headers = {"authorization": auth_token} if auth_token else {}

    with closing(http.client.HTTPConnection(fledge_url)) as connection:
        connection.request("PUT", '/fledge/restart', headers=headers, body=json.dumps({}))
        r = connection.getresponse()
        assert 200 == r.status
        r = r.read().decode()
        jdoc = json.loads(r)
        assert "Fledge restart has been scheduled." == jdoc['message']

    print(f"Waiting for Fledge to restart... (Initial wait: {wait_time}s)")
    time.sleep(wait_time)
    start_time = time.time()
    max_retries = 5
    jdoc = {}
    for attempt in range(max_retries):
        try:
            with closing(http.client.HTTPConnection(fledge_url)) as connection:
                connection.request("GET", "/fledge/ping", headers=headers)
                response = connection.getresponse()
                if response.status == 200:
                    r = response.read().decode()
                    jdoc = json.loads(r)
                    break
                elif response.status == 401:
                    jdoc = {"message": "Unauthorized"}
                    break
        except:
            pass  # Continue trying
        time.sleep(wait_time * 5)
    if not jdoc:
        elapsed = round(time.time() - start_time, 2)
        raise AssertionError(f"Failed to restart Fledge after {elapsed} seconds.")
    else:
        # Additional time is necessary to ensure that other endpoints are prepared
        time.sleep(wait_time * 5)
    return jdoc


@pytest.fixture
def fogbench_host(request):
    return request.config.getoption("--fogbench-host")


@pytest.fixture
def fogbench_port(request):
    return request.config.getoption("--fogbench-port")


@pytest.fixture
def azure_host(request):
    return request.config.getoption("--azure-host")


@pytest.fixture
def azure_device(request):
    return request.config.getoption("--azure-device")


@pytest.fixture
def azure_key(request):
    return request.config.getoption("--azure-key")


@pytest.fixture
def azure_storage_account_url(request):
    return request.config.getoption("--azure-storage-account-url")


@pytest.fixture
def azure_storage_account_key(request):
    return request.config.getoption("--azure-storage-account-key")


@pytest.fixture
def azure_storage_container(request):
    return request.config.getoption("--azure-storage-container")


@pytest.fixture
def run_time(request):
    return request.config.getoption("--run-time")

