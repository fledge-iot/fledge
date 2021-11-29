# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Test Filters Package System tests:
        fledge-south-http-south south plugin
        fledge-filter-expression, fledge-filter-python35 filter plugins
"""

# FIXME: This test requires aiocoap,cbor pip packages installed explicitly due to FOGL-3500

__author__ = "Yash Tatkondawar"
__copyright__ = "Copyright (c) 2019 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import subprocess
import http.client
import json
import os
import time
import urllib.parse
from pathlib import Path
import utils
import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPTS_DIR_ROOT = "{}/tests/system/python/scripts/package/".format(PROJECT_ROOT)
DATA_DIR_ROOT = "{}/tests/system/python/packages/data/".format(PROJECT_ROOT)

HTTP_SOUTH_SVC_NAME = "South_http #1"
ASSET_NAME_PY35 = "end_to_end_py35"
ASSET_NAME_SP = "end_to_end_sp"
ASSET_NAME_EMA = "end_to_end_ema"
TEMPLATE_NAME = "template.json"
SENSOR_VALUE = 12.25


@pytest.fixture
def reset_fledge(wait_time):
    try:
        subprocess.run(["cd {} && ./reset"
                       .format(SCRIPTS_DIR_ROOT)], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "reset package script failed!"


def call_fogbench(wait_time):
    execute_fogbench = 'cd {}/extras/python ;python3 -m fogbench -t $FLEDGE_ROOT/data/tests/{} ' \
                       '-p http -O 10'.format(PROJECT_ROOT, TEMPLATE_NAME)
    exit_code = os.system(execute_fogbench)
    assert 0 == exit_code
    time.sleep(wait_time)


@pytest.fixture
def add_south_http_with_filter(add_south, add_filter, fledge_url):
    south_plugin = "http-south"
    add_south(south_plugin, None, fledge_url, service_name="{}".format(HTTP_SOUTH_SVC_NAME),
              plugin_discovery_name="http_south", installation_type='package')

    filter_cfg_scale = {"enable": "true"}
    add_filter("python35", None, "py35", filter_cfg_scale, fledge_url, HTTP_SOUTH_SVC_NAME, installation_type='package')

    yield add_south_http_with_filter


@pytest.fixture
def add_filter_expression(add_filter, fledge_url):
    filter_cfg_exp = {"name": "double", "expression": "sensor*2", "enable": "true"}
    add_filter("expression", None, "expr", filter_cfg_exp, fledge_url, HTTP_SOUTH_SVC_NAME, installation_type='package')


def generate_json(asset_name):
    subprocess.run(["cd $FLEDGE_ROOT/data && mkdir -p tests"], shell=True, check=True)

    fogbench_template_path = os.path.join(
        os.path.expandvars('${FLEDGE_ROOT}'), 'data/tests/{}'.format(TEMPLATE_NAME))
    with open(fogbench_template_path, "w") as f:
        f.write(
            '[{"name": "%s", "sensor_values": '
            '[{"name": "sensor", "type": "number", "min": %f, "max": %f, "precision": 2}]}]' % (
                asset_name, SENSOR_VALUE, SENSOR_VALUE))


def verify_south_added(fledge_url, name):
    get_url = "/fledge/south"
    result = utils.get_request(fledge_url, get_url)
    assert len(result["services"])
    assert "name" in result["services"][0]
    assert name == result["services"][0]["name"]


def verify_ping(fledge_url):
    get_url = "/fledge/ping"
    ping_result = utils.get_request(fledge_url, get_url)
    assert "dataRead" in ping_result
    assert 0 < ping_result['dataRead'], "data NOT seen in ping header"
    return ping_result


def verify_asset(fledge_url, asset_name):
    asset_name = "http-" + asset_name
    get_url = "/fledge/asset"
    result = utils.get_request(fledge_url, get_url)
    assert len(result), "No asset found"
    assert "assetCode" in result[0]
    assert asset_name == result[0]["assetCode"]
    return result[0]


def verify_readings(fledge_url, asset_name):
    asset_name = "http-" + asset_name
    get_url = "/fledge/asset/{}".format(asset_name)
    result = utils.get_request(fledge_url, get_url)
    assert len(result), "No readings found"
    assert "reading" in result[0]
    return result[0]


class TestPython35:
    def test_filter_python35_with_uploaded_script(self, clean_setup_fledge_packages, reset_fledge,
                                                  add_south_http_with_filter, fledge_url, wait_time):
        # Wait until south service is created
        time.sleep(wait_time * 2)
        verify_south_added(fledge_url, HTTP_SOUTH_SVC_NAME)

        generate_json(ASSET_NAME_PY35)

        call_fogbench(wait_time)

        ping_response = verify_ping(fledge_url)
        assert 10 == ping_response["dataRead"]

        asset_response = verify_asset(fledge_url, ASSET_NAME_PY35)
        assert 10 == asset_response["count"]

        reading_resp = verify_readings(fledge_url, ASSET_NAME_PY35)
        assert 12.25 == reading_resp["reading"]["sensor"]

        url = fledge_url + urllib.parse.quote('/fledge/category/{}_py35/script/upload'
                                              .format(HTTP_SOUTH_SVC_NAME))
        script_path = 'script=@{}/readings35.py'.format(DATA_DIR_ROOT)
        upload_script = "curl -sX POST '{}' -F '{}'".format(url, script_path)
        exit_code = os.system(upload_script)
        assert 0 == exit_code

        call_fogbench(wait_time)

        ping_response = verify_ping(fledge_url)
        assert 20 == ping_response["dataRead"]

        asset_response = verify_asset(fledge_url, ASSET_NAME_PY35)
        assert 20 == asset_response["count"]

        reading_resp = verify_readings(fledge_url, ASSET_NAME_PY35)
        assert 2.45 == reading_resp["reading"]["sensor"]

    def test_filter_python35_with_updated_content(self, fledge_url, retries, wait_time):
        copy_file = "cp {}/readings35.py {}/readings35.py.bak".format(DATA_DIR_ROOT, DATA_DIR_ROOT)
        exit_code = os.system(copy_file)
        assert 0 == exit_code

        sed_cmd = "sed -i \"s+newVal .*+newVal = reading[key] * 10+\" {}/readings35.py".format(DATA_DIR_ROOT)
        exit_code = os.system(sed_cmd)
        assert 0 == exit_code

        url = fledge_url + urllib.parse.quote('/fledge/category/{}_py35/script/upload'
                                              .format(HTTP_SOUTH_SVC_NAME))
        script_path = 'script=@{}/readings35.py'.format(DATA_DIR_ROOT)
        upload_script = "curl -sX POST '{}' -F '{}'".format(url, script_path)
        exit_code = os.system(upload_script)
        assert 0 == exit_code

        time.sleep(wait_time)

        call_fogbench(wait_time)

        ping_response = verify_ping(fledge_url)
        assert 30 == ping_response["dataRead"]

        asset_response = verify_asset(fledge_url, ASSET_NAME_PY35)
        assert 30 == asset_response["count"]

        reading_resp = verify_readings(fledge_url, ASSET_NAME_PY35)
        assert 122.5 == reading_resp["reading"]["sensor"]

        move_file = "mv {}/readings35.py.bak {}/readings35.py".format(DATA_DIR_ROOT, DATA_DIR_ROOT)
        exit_code = os.system(move_file)
        assert 0 == exit_code, "{} cmd failed!".format(move_file)

    def test_filter_python35_disable_enable(self, fledge_url, retries, wait_time):
        data = {"enable": "false"}
        utils.put_request(fledge_url, urllib.parse.quote("/fledge/category/{}_py35".format(HTTP_SOUTH_SVC_NAME),
                                                         safe='?,=,&,/'), data)

        call_fogbench(wait_time)

        ping_response = verify_ping(fledge_url)
        assert 40 == ping_response["dataRead"]

        asset_response = verify_asset(fledge_url, ASSET_NAME_PY35)
        assert 40 == asset_response["count"]

        reading_resp = verify_readings(fledge_url, ASSET_NAME_PY35)
        assert 12.25 == reading_resp["reading"]["sensor"]

        data = {"enable": "true"}
        utils.put_request(fledge_url, urllib.parse.quote("/fledge/category/{}_py35"
                                                         .format(HTTP_SOUTH_SVC_NAME), safe='?,=,&,/'), data)

        call_fogbench(wait_time)

        ping_response = verify_ping(fledge_url)
        assert 50 == ping_response["dataRead"]

        asset_response = verify_asset(fledge_url, ASSET_NAME_PY35)
        assert 50 == asset_response["count"]

        reading_resp = verify_readings(fledge_url, ASSET_NAME_PY35)
        assert 122.5 == reading_resp["reading"]["sensor"]

    def test_filter_python35_expression(self, add_filter_expression, fledge_url, wait_time):
        data = {"schedule_name": "{}".format(HTTP_SOUTH_SVC_NAME)}
        put_url = "/fledge/schedule/disable"
        utils.put_request(fledge_url, put_url, data)

        data = {"schedule_name": "{}".format(HTTP_SOUTH_SVC_NAME)}
        put_url = "/fledge/schedule/enable"
        utils.put_request(fledge_url, put_url, data)

        time.sleep(wait_time)

        call_fogbench(wait_time)

        ping_response = verify_ping(fledge_url)
        assert 60 == ping_response["dataRead"]

        asset_response = verify_asset(fledge_url, ASSET_NAME_PY35)
        assert 60 == asset_response["count"]

        reading_resp = verify_readings(fledge_url, ASSET_NAME_PY35)
        assert 122.5 == reading_resp["reading"]["sensor"]
        assert 245.0 == reading_resp["reading"]["double"]

    def test_delete_filter_python35(self, fledge_url, wait_time):
        data = {"pipeline": ["expr"]}
        put_url = "/fledge/filter/{}/pipeline?allow_duplicates=true&append_filter=false" \
            .format(HTTP_SOUTH_SVC_NAME)
        utils.put_request(fledge_url, urllib.parse.quote(put_url, safe='?,=,&,/'), data)

        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", '/fledge/filter/py35')
        res = conn.getresponse()
        assert 200 == res.status, "ERROR! Failed to delete filter"

        call_fogbench(wait_time)

        ping_response = verify_ping(fledge_url)
        assert 70 == ping_response["dataRead"]

        asset_response = verify_asset(fledge_url, ASSET_NAME_PY35)
        assert 70 == asset_response["count"]

        reading_resp = verify_readings(fledge_url, ASSET_NAME_PY35)
        assert 12.25 == reading_resp["reading"]["sensor"]
        assert 24.5 == reading_resp["reading"]["double"]

    def test_filter_python35_by_enabling_disabling_south(self, fledge_url, wait_time):
        data = {"schedule_name": "{}".format(HTTP_SOUTH_SVC_NAME)}
        put_url = "/fledge/schedule/disable"
        utils.put_request(fledge_url, put_url, data)

        time.sleep(wait_time)

        get_url = "/fledge/south"
        result = utils.get_request(fledge_url, get_url)
        assert HTTP_SOUTH_SVC_NAME == result["services"][0]["name"]
        assert "shutdown" == result["services"][0]["status"]

        data = {"name": "py35", "plugin": "python35", "filter_config": {"enable": "true"}}
        utils.post_request(fledge_url, "/fledge/filter", data)

        data = {"pipeline": ["py35"]}
        put_url = "/fledge/filter/{}/pipeline?allow_duplicates=true&append_filter=true" \
            .format(HTTP_SOUTH_SVC_NAME)
        utils.put_request(fledge_url, urllib.parse.quote(put_url, safe='?,=,&,/'), data)

        url = fledge_url + urllib.parse.quote('/fledge/category/{}_py35/script/upload'
                                              .format(HTTP_SOUTH_SVC_NAME))
        script_path = 'script=@{}/readings35.py'.format(DATA_DIR_ROOT)
        upload_script = "curl -sX POST '{}' -F '{}'".format(url, script_path)
        exit_code = os.system(upload_script)
        assert 0 == exit_code

        data = {"schedule_name": HTTP_SOUTH_SVC_NAME}
        put_url = "/fledge/schedule/enable"
        utils.put_request(fledge_url, put_url, data)

        time.sleep(wait_time)

        call_fogbench(wait_time)

        ping_response = verify_ping(fledge_url)
        assert 80 == ping_response["dataRead"]

        asset_response = verify_asset(fledge_url, ASSET_NAME_PY35)
        assert 80 == asset_response["count"]

        reading_resp = verify_readings(fledge_url, ASSET_NAME_PY35)
        assert 2.45 == reading_resp["reading"]["sensor"]
        assert 4.9 == reading_resp["reading"]["double"]

    def test_delete_south_service(self, fledge_url):
        conn = http.client.HTTPConnection(fledge_url)
        conn.request("DELETE", urllib.parse.quote('/fledge/service/{}'
                                                  .format(HTTP_SOUTH_SVC_NAME), safe='?,=,&,/'))
        res = conn.getresponse()
        assert 200 == res.status, "ERROR! Failed to delete service"

        get_url = "/fledge/south"
        result = utils.get_request(fledge_url, get_url)
        assert 0 == len(result["services"])

        filename = "{}_py35_script_readings35.py".format(HTTP_SOUTH_SVC_NAME).lower()
        filepath = "$FLEDGE_ROOT/data/scripts/{}".format(filename)
        assert False == os.path.isfile('{}'.format(filepath))

