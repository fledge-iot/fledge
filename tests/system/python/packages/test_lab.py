# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Lab packages System tests
"""

__author__ = "Yash Tatkondawar"
__copyright__ = "Copyright (c) 2019 Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

import subprocess
import http.client
import json
import pytest
import os
import time
import urllib.parse

SCRIPTS_DIR_ROOT = os.environ.get("FOGLAMP_ROOT") + "/tests/system/lab/scripts/"


# TODO:pass version to install script
def setup_module(module):
    try:
        subprocess.run(["cd $FOGLAMP_ROOT/tests/system/lab && ./remove"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "remove package script failed!"

    try:
        subprocess.run(["cd $FOGLAMP_ROOT/tests/system/lab && ./install"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "install package script failed"


def post_request(foglamp_url, post_url, payload):
    conn = http.client.HTTPConnection(foglamp_url)
    conn.request("POST", post_url, json.dumps(payload))
    res = conn.getresponse()
    assert 200 == res.status
    res = res.read().decode()
    r = json.loads(res)
    # print(r)
    return r


def get_request(foglamp_url, get_url):
    con = http.client.HTTPConnection(foglamp_url)
    con.request("GET", get_url)
    resp = con.getresponse()
    r = json.loads(resp.read().decode())
    # print(r)
    return r


def put_request(foglamp_url, put_url, payload):
    conn = http.client.HTTPConnection(foglamp_url)
    conn.request("PUT", put_url, json.dumps(payload))
    res = conn.getresponse()
    assert 200 == res.status
    r = json.loads(res.read().decode())
    # print(r)
    return r


class TestSouth:
    def test_south_sinusoid(self, foglamp_url, retries, wait_time):
        data = {"name": "Sine", "type": "south", "plugin": "sinusoid", "enabled": True, "config": {}}
        post_url = "/foglamp/service"
        post_request(foglamp_url, post_url, data)

        time.sleep(wait_time * 2)

        while retries:
            get_url = "/foglamp/south"
            result = get_request(foglamp_url, get_url)

            assert len(result["services"])
            assert "name" in result["services"][0]
            assert "Sine" == result["services"][0]["name"]

            assert "assets" in result["services"][0]
            if "asset" in result["services"][0]["assets"][0]:
                assert "sinusoid" == result["services"][0]["assets"][0]["asset"]
                break
            retries -= 1

        if retries == 0:
            assert False, "TIMEOUT! sinusoid data NOT seen in South tab." + foglamp_url + "/foglamp/south"

    def test_sinusoid_in_asset(self, foglamp_url):
        get_url = "/foglamp/asset"
        result = get_request(foglamp_url, get_url)
        assert len(result)
        assert "assetCode" in result[0]
        assert "sinusoid" == result[0]["assetCode"], "sinusoid data NOT seen in Asset tab"

    def test_sinusoid_ping(self, foglamp_url):
        get_url = "/foglamp/ping"
        ping_result = get_request(foglamp_url, get_url)
        assert "dataRead" in ping_result
        assert 0 < ping_result['dataRead'], "sinusoid data NOT seen in ping header"

    def test_sinusoid_graph(self, foglamp_url):
        get_url = "/foglamp/asset/sinusoid?seconds=600"
        result = get_request(foglamp_url, get_url)
        assert len(result)
        assert "reading" in result[0]
        assert "sinusoid" in result[0]["reading"]
        assert 0 < result[0]["reading"]["sinusoid"]

    def test_delete_south_sinusoid(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("DELETE", '/foglamp/service/Sine')
        res = conn.getresponse()
        assert 200 == res.status
        
        get_url = "/foglamp/south"
        result = get_request(foglamp_url, get_url)
        assert [] == result["services"]
        
        get_url = "/foglamp/service"
        result = get_request(foglamp_url, get_url)
        assert "Sine" not in [s["name"] for s in result["services"]]
                  
        get_url = "/foglamp/category"
        result = get_request(foglamp_url, get_url)
        assert "Sine" not in [s["key"] for s in result["categories"]]
        
        get_url = "/foglamp/schedule"
        result = get_request(foglamp_url, get_url)
        assert "Sine" not in [s["name"] for s in result["schedules"]]


@pytest.mark.skip(reason="FIXME: To enable North verification on the basis of "
                         "--skip-verify-north-interface fixture value")
class TestNorth:

    def test_north_pi_egress(self, foglamp_url, pi_host, pi_port, pi_token, retries):
        payload = {"name": "PI Server", "plugin": "PI_Server_V2", "type": "north", "schedule_repeat": 30,
                   "schedule_type": "3", "schedule_enabled": True,
                   "config": {"URL": {"value": "https://{}:{}/ingress/messages".format(pi_host, pi_port)},
                              "producerToken": {"value": pi_token}, "compression": {"value": "false"}}}
        post_request(foglamp_url, "/foglamp/scheduled/task", payload)

        while retries:
            r = get_request(foglamp_url, "/foglamp/north")
            if "sent" in r[0]:
                assert 0 < r[0]["sent"]
                break
            retries -= 1

        if retries == 0:
            assert False, "TIMEOUT! PI data sent not seen in North tab." + foglamp_url + "/foglamp/north"

    def test_north_ping(self, foglamp_url):
        r = get_request(foglamp_url, "/foglamp/ping")
        assert "dataSent" in r
        assert 0 < r['dataSent']

    def test_north_stats_history(self, foglamp_url, retries, wait_time):
        while retries:
            # time.sleep(wait_time)
            get_url = "/foglamp/statistics/history?minutes=10"
            r = get_request(foglamp_url, get_url)
            if "PI Server" in r["statistics"][0]:
                assert 0 < r["statistics"][0]["PI Server"]
                break
            retries -= 1

        if retries == 0:
            assert False, "TIMEOUT! PI data sent not seen in sent graph. " + foglamp_url + "/foglamp/statistics/history?minutes=10"

       
class TestSinusoidMaxSquare:

    def add_sinusoid_with_square_and_max_filter(self, foglamp_url):
        data = {"name": "Sine", "type": "south", "plugin": "sinusoid", "enabled": True, "config": {}}
        post_url = "/foglamp/service"
        post_request(foglamp_url, post_url, data)

        # Square expression filter
        data = {"name": "Square", "plugin": "expression",
                "filter_config": {"name": "square", "expression": "if(sinusoid>0,0.5,-0.5)", "enable": "true"}}
        post_request(foglamp_url, "/foglamp/filter", data)

        data = {"pipeline": ["Square"]}
        put_url = "/foglamp/filter/Sine/pipeline?allow_duplicates=true&append_filter=true"
        put_request(foglamp_url, put_url, data)

        # Max expression filter
        data = {"name": "Max2", "plugin": "expression",
                "filter_config": {"name": "max", "expression": "max(sinusoid, square)", "enable": "true"}}
        post_url = "/foglamp/filter"
        post_request(foglamp_url, post_url, data)

        data = {"pipeline": ["Max2"]}
        put_url = "/foglamp/filter/Sine/pipeline?allow_duplicates=true&append_filter=true"
        put_request(foglamp_url, put_url, data)

    def test_sinusoid_max_square(self, foglamp_url, retries, wait_time):
        self.add_sinusoid_with_square_and_max_filter(foglamp_url)
        time.sleep(wait_time * 2)
        while retries:
            get_url = "/foglamp/asset/sinusoid?seconds=600"
            r = get_request(foglamp_url, get_url)
            if "square" in r[0]["reading"] and "max" in r[0]["reading"]:
                assert 0 < r[0]["reading"]["square"]
                assert 0 < r[0]["reading"]["max"]
                break
            retries -= 1

        if retries == 0:
            assert False, "TIMEOUT! square and max data not seen in sinusoid graph." + foglamp_url + "/foglamp/asset/sinusoid?seconds=600"


class TestRandomwalk:

    def test_add_randomwalk_south(self, foglamp_url, wait_time):
        payload = {"name": "Random", "type": "south", "plugin": "randomwalk", "enabled": True, "config": {}}
        post_url = "/foglamp/service"
        post_request(foglamp_url, post_url, payload)

        time.sleep(wait_time*2)

        # verify Random service
        get_url = "/foglamp/service"
        result = get_request(foglamp_url, get_url)
        assert "Random" in [s["name"] for s in result["services"]]

    def test_randomwalk_with_filter_python35(self, foglamp_url, wait_time, retries):
        data = {"name": "Ema", "plugin": "python35", "filter_config": {"config": {"rate": 0.07}, "enable": "true"}}
        post_request(foglamp_url, "/foglamp/filter", data)

        data = {"pipeline": ["Ema"]}
        put_url = "/foglamp/filter/Random/pipeline?allow_duplicates=true&append_filter=true"
        put_request(foglamp_url, put_url, data)

        url = foglamp_url + '/foglamp/category/Random_Ema/script/upload'
        script_path = 'script=@{}/ema.py'.format(SCRIPTS_DIR_ROOT)
        upload_script = "curl -sX POST '{}' -F '{}'".format(url, script_path)
        exit_code = os.system(upload_script)
        assert exit_code == 0

        time.sleep(wait_time)

        while retries:
            get_url = "/foglamp/asset/randomwalk?seconds=600"
            data = get_request(foglamp_url, get_url)
            if len(data) and "randomwalk" in data[0]["reading"] and "ema" in data[0]["reading"]:
                assert 0 < data[0]["reading"]["randomwalk"]
                assert 0 < data[0]["reading"]["ema"]
                # TODO: verify asset tracker entry
                break
            retries -= 1

        if retries == 0:
            assert False, "TIMEOUT! randomwalk and ema data not seen in randomwalk graph." + foglamp_url + "/foglamp/asset/randomwalk?seconds=600"

    def test_delete_randomwalk_south(self, foglamp_url):
        conn = http.client.HTTPConnection(foglamp_url)
        conn.request("DELETE", '/foglamp/service/Random')
        res = conn.getresponse()
        assert 200 == res.status, "ERROR! Failed to delete randomwalk service"

        get_url = "/foglamp/service"
        result = get_request(foglamp_url, get_url)
        assert "Random" not in [s["name"] for s in result["services"]]

        get_url = "/foglamp/category"
        result = get_request(foglamp_url, get_url)
        assert "Random" not in [c["key"] for c in result["categories"]]

        get_url = "/foglamp/schedule"
        result = get_request(foglamp_url, get_url)
        assert "Random" not in [sch["name"] for sch in result["schedules"]]


class TestRandomwalk1:

    def test_randomwalk1_south_with_python35_filter(self, foglamp_url, wait_time, retries):
        print("Add Randomwalk south service again ...")
        data = {"name": "Random1", "type": "south", "plugin": "randomwalk", "enabled": True,
                "config": {"assetName": {"value": "randomwalk1"}}}
        post_request(foglamp_url, "/foglamp/service", data)

        # need to wait for FogLAMP to be ready to accept python file
        time.sleep(wait_time)

        data = {"name": "PF", "plugin": "python35", "filter_config": {"config": {"rate": 0.07}, "enable": "true"}}
        post_request(foglamp_url, "/foglamp/filter", data)

        # Apply PF to Random
        data = {"pipeline": ["PF"]}
        put_url = "/foglamp/filter/Random1/pipeline?allow_duplicates=true&append_filter=true"
        put_request(foglamp_url, put_url, data)

        print("upload trendc script...")
        url = foglamp_url + '/foglamp/category/Random1_PF/script/upload'

        script_path = 'script=@{}/trendc.py'.format(SCRIPTS_DIR_ROOT)
        upload_script = "curl -sX POST '{}' -F '{}'".format(url, script_path)
        exit_code = os.system(upload_script)
        assert exit_code == 0

        time.sleep(wait_time)

        while retries:
            get_url = "/foglamp/asset/randomwalk1?seconds=600"
            data = get_request(foglamp_url, get_url)
            if len(data) and "randomwalk" in data[0]["reading"] and "ema_long" in data[0]["reading"]:
                assert 0 < data[0]["reading"]["randomwalk"]
                assert 0 < data[0]["reading"]["ema_long"]
                # TODO: verify ema_short and trend in reading
                # TODO: verify asset tracker entry
                break
            retries -= 1

        if retries == 0:
            assert False, "TIMEOUT! randomwalk and ema_long data not seen in randomwalk1 graph." + foglamp_url + "/foglamp/asset/randomwalk1?seconds=600"

    def test_randomwalk1_python35_filter_script_content_reconfig(self, foglamp_url, retries, wait_time):
        copy_file = "cp {}/trendc.py {}/trendc.py.bak".format(SCRIPTS_DIR_ROOT, SCRIPTS_DIR_ROOT)
        exit_code = os.system(copy_file)
        assert exit_code == 0

        sed_cmd = "sed -i \"s/reading\[b'ema_long/reading\[b'ema_longX/g\" {}/trendc.py".format(SCRIPTS_DIR_ROOT)
        exit_code = os.system(sed_cmd)
        assert exit_code == 0

        print("upload modified trendc script...")
        url = foglamp_url + '/foglamp/category/Random1_PF/script/upload'
        script_path = 'script=@{}/trendc.py'.format(SCRIPTS_DIR_ROOT)
        upload_script = "curl -sX POST '{}' -F '{}'".format(url, script_path)
        exit_code = os.system(upload_script)
        assert exit_code == 0

        time.sleep(wait_time)

        while retries:
            get_url = "/foglamp/asset/randomwalk1?seconds=600"
            data = get_request(foglamp_url, get_url)
            if len(data) and "randomwalk" in data[0]["reading"] and "ema_longX" in data[0]["reading"]:
                assert 0 < data[0]["reading"]["randomwalk"]
                assert 0 < data[0]["reading"]["ema_longX"]
                break
                # TODO: verify asset tracker entry
            retries -= 1

        move_file = "mv {}/trendc.py.bak {}/trendc.py".format(SCRIPTS_DIR_ROOT, SCRIPTS_DIR_ROOT)
        exit_code = os.system(move_file)
        assert exit_code == 0, "{} cmd failed!".format(move_file)

        if retries == 0:
            assert False, "TIMEOUT! randomwalk and ema_longX data not seen in randomwalk1 graph." + foglamp_url + "/foglamp/asset/randomwalk1?seconds=600"

    def test_randomwalk1_python35_filter_script_reconfig(self, foglamp_url, retries, wait_time):
        url = foglamp_url + '/foglamp/category/Random1_PF/script/upload'
        script_path = 'script=@{}/ema.py'.format(SCRIPTS_DIR_ROOT)
        upload_script = "curl -sX POST '{}' -F '{}'".format(url, script_path)
        exit_code = os.system(upload_script)
        assert exit_code == 0

        time.sleep(wait_time)

        while retries:
            get_url = "/foglamp/asset/randomwalk1?seconds=600"
            data = get_request(foglamp_url, get_url)
            if len(data) and "randomwalk" in data[0]["reading"] and "ema" in data[0]["reading"]:
                assert 0 < data[0]["reading"]["randomwalk"]
                assert 0 < data[0]["reading"]["ema"]
                # TODO: verify asset tracker entry
                break
            retries -= 1

        if retries == 0:
            assert False, "TIMEOUT! randomwalk and ema data not seen in randomwalk1 graph." + foglamp_url + "/foglamp/asset/randomwalk1?seconds=600"


@pytest.mark.skipif(os.uname()[4][:3] != 'arm', reason="only compatible with arm architecture")
class TestEnviroPhat:
    def test_enviro_phat(self, foglamp_url, retries, wait_time):
        data = {"name": "Enviro", "type": "south", "plugin": "envirophat", "enabled": True,
                "config": {"assetNamePrefix": {"value": "e_"}}}
        post_request(foglamp_url, "/foglamp/service", data)

        data = {"name": "Fahrenheit", "plugin": "expression",
                "filter_config": {"name": "temp_fahr", "expression": "temperature*1.8+32", "enable": "true"}}
        post_request(foglamp_url, "/foglamp/filter", data)

        data = {"pipeline": ["Fahrenheit"]}
        put_url = "/foglamp/filter/Enviro/pipeline?allow_duplicates=true&append_filter=true"
        put_request(foglamp_url, put_url, data)

        time.sleep(wait_time*2)

        while retries:
            get_url = "/foglamp/asset/e_weather?seconds=600"
            data = get_request(foglamp_url, get_url)
            if len(data) and "temperature" in data[0]["reading"] and "max" in data[0]["reading"]:
                assert data[0]["reading"]["temperature"] != ""
                assert data[0]["reading"]["temp_fahr"] != ""
                break
            retries -= 1

        if retries == 0:
            assert False, "TIMEOUT! temperature and max data not seen in e_weather graph." + foglamp_url + "/foglamp/asset/e_weather?seconds=600"


class TestEventEngine:
    """This will test the Notification service in foglamp."""

    def test_event_engine(self, foglamp_url, retries, wait_time):
        payload = {"name": "FogLAMP Notifications", "type": "notification", "enabled": True}
        post_url = "/foglamp/service"
        post_request(foglamp_url, post_url, payload)

        time.sleep(wait_time)

        svc_found = False
        while retries:
            get_url = "/foglamp/service"
            resp = get_request(foglamp_url, get_url)
            for item in resp["services"]:
                if item['name'] == "FogLAMP Notifications":
                    svc_found = True
                    assert item['status'] == "running"
                    break  # break for loop
            if svc_found:
                break  # break while loop
            retries -= 1

        if retries == 0:
            assert False, "TIMEOUT! event engine is not running." + foglamp_url + "/foglamp/service"

    def test_positive_sine_notification(self, foglamp_url, retries, wait_time):
        """Add Notification with Threshold Rule and Asset Notification (Positive Sine)"""

        payload = {"name": "Positive Sine", "description": "Positive Sine notification instance", "rule": "Threshold",
                   "channel": "asset", "notification_type": "retriggered", "enabled": True}
        post_url = "/foglamp/notification"
        post_request(foglamp_url, post_url, payload)

        payload = {"asset": "sinusoid", "datapoint": "sinusoid"}
        put_url = "/foglamp/category/rulePositive Sine"
        put_request(foglamp_url, urllib.parse.quote(put_url), payload)

        payload = {"asset": "positive_sine", "description": "positive", "enable": "true"}
        put_url = "/foglamp/category/deliveryPositive Sine"
        put_request(foglamp_url, urllib.parse.quote(put_url), payload)

        time.sleep(wait_time)

        while retries:
            get_url = "/foglamp/asset/positive_sine?seconds=600"
            resp = get_request(foglamp_url, get_url)
            if len(resp) and "event" in resp[0]["reading"] and "rule" in resp[0]["reading"]:
                assert resp[0]["reading"]["event"] == "triggered"
                assert resp[0]["reading"]["rule"] == "Positive Sine"
                break
            retries -= 1

        if retries == 0:
            assert False, "TIMEOUT! positive_sine event not fired." + foglamp_url + "/foglamp/asset/positive_sine?seconds=600"

    def test_negative_sine_notification(self, foglamp_url, remove_data_file, retries, wait_time):
        """Add Notification with Threshold Rule and Asset Notification (Negative Sine)"""
        remove_data_file("/tmp/out")

        payload = {"name": "Negative Sine", "description": "Negative Sine notification instance", "rule": "Threshold",
                   "channel": "python35", "notification_type": "retriggered", "enabled": True}
        post_request(foglamp_url, "/foglamp/notification", payload)

        # Upload Python Script (write_out.py)
        url = foglamp_url + urllib.parse.quote('/foglamp/category/deliveryNegative Sine/script/upload')
        script_path = 'script=@{}/write_out.py'.format(SCRIPTS_DIR_ROOT)
        upload_script = "curl -sX POST '{}' -F '{}'".format(url, script_path)
        exit_code = os.system(upload_script)
        assert exit_code == 0

        payload = {"asset": "sinusoid", "datapoint": "sinusoid", "condition": "<"}
        put_request(foglamp_url, urllib.parse.quote("/foglamp/category/ruleNegative Sine"), payload)

        payload = {"enable": "true"}
        put_request(foglamp_url, urllib.parse.quote("/foglamp/category/deliveryNegative Sine"), payload)

        s = wait_time * 2
        for _ in range(retries):
            if os.path.exists("/tmp/out"):
                break
            time.sleep(s)
            print("sleeping for {}s before retrying the existence check of '/tmp/out'".format(s))

        if not os.path.exists("/tmp/out"):
            assert False, "TIMEOUT! negative_sine event not fired. No /tmp/out file."

    def test_event_toggled_sent_clear(self, foglamp_url, wait_time, retries):
        print("Add sinusoid")
        payload = {"name": "sin #1", "plugin": "sinusoid", "type": "south", "enabled": True}
        post_url = "/foglamp/service"
        resp = post_request(foglamp_url, post_url, payload)
        assert resp["id"] != "", "Failed to add sin #1"
        assert resp["name"] == "sin #1", "Failed to add sin #1"

        print("Create event instance with threshold and asset; with notification trigger type toggled")
        payload = {"name": "test #1", "description": "test notification instance", "rule": "Threshold",
                   "channel": "asset", "notification_type": "toggled", "enabled": True}
        post_url = "/foglamp/notification"
        post_request(foglamp_url, post_url, payload)
        
        get_url = "/foglamp/notification"
        resp = get_request(foglamp_url, get_url)
        assert "test #1" in [s["name"] for s in resp["notifications"]]

        print("Set rule")
        payload = {"asset": "sinusoid", "datapoint": "sinusoid", "trigger_value": "0.8"}
        put_url = "/foglamp/category/ruletest #1"
        put_request(foglamp_url, urllib.parse.quote(put_url), payload)
        
        get_url = "/foglamp/category/ruletest #1"
        resp = get_request(foglamp_url, urllib.parse.quote(get_url))
        assert resp["asset"]["value"] == "sinusoid"
        assert resp["datapoint"]["value"] == "sinusoid"
        assert resp["trigger_value"]["value"] == "0.8"

        print("Set delivery")
        payload = {"asset": "sin 0.8", "description": "asset notification", "enable": "true"}
        put_url = "/foglamp/category/deliverytest #1"
        put_request(foglamp_url, urllib.parse.quote(put_url), payload)

        get_url = "/foglamp/category/deliverytest #1"
        resp = get_request(foglamp_url, urllib.parse.quote(get_url))
        assert resp["asset"]["value"] == "sin 0.8"
        assert resp["enable"]["value"] == "true"

        s = wait_time*2

        print("Verify sin 0.8 has been created")
        while retries:
            time.sleep(s)
            get_url = "/foglamp/asset/sin 0.8"
            resp = get_request(foglamp_url, urllib.parse.quote(get_url))
            if len(resp) > 0:
                assert True
                break
            retries -= 1

        # TODO: FOGL-3115 verify asset tracker entry

        if retries == 0:
            assert False, "TIMEOUT! sin 0.8 event not fired." + foglamp_url + "/foglamp/asset/sin 0.8"

        print("When rule is triggred, There should be audit entries for NTFSN & NTFCL")
        get_url = "/foglamp/audit?limit=1&source=NTFSN&severity=INFORMATION"
        resp = get_request(foglamp_url, get_url)
        assert len(resp['audit'])
        assert "test #1" in [s["details"]["name"] for s in resp["audit"]]
        for audit_detail in resp['audit']:
            if "test #1" == audit_detail['details']['name']:
                assert "INFORMATION" == audit_detail['severity']
                assert "NTFSN" == audit_detail['source']

        time.sleep(2)  # let clear event to trigger

        get_url = "/foglamp/audit?limit=1&source=NTFCL&severity=INFORMATION"
        resp = get_request(foglamp_url, get_url)
        assert len(resp['audit'])
        assert "test #1" in [s["details"]["name"] for s in resp["audit"]]
        for audit_detail in resp['audit']:
            if "test #1" == audit_detail['details']['name']:
                assert "INFORMATION" == audit_detail['severity']
                assert "NTFCL" == audit_detail['source']


def teardown_module(module):
    try:
        subprocess.run(["cd $FOGLAMP_ROOT/tests/system/lab && ./remove"], shell=True, check=True)
    except subprocess.CalledProcessError:
        assert False, "remove package script failed!"
