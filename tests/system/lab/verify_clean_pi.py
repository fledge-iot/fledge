import argparse
import http.client
import json
import base64
import ssl
import time

retry_count = 0
data_from_pi = None
retries = 6
wait_time = 10

parser = argparse.ArgumentParser(description="PI server",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--pi-host", action="store", default="pi-server",
                    help="PI Server Host Name/IP")
parser.add_argument("--pi-port", action="store", default="5460", type=int,
                    help="PI Server Port")
parser.add_argument("--pi-db", action="store", default="pi-server-db",
                    help="PI Server database")
parser.add_argument("--pi-admin", action="store", default="pi-server-uid",
                    help="PI Server user login")
parser.add_argument("--pi-passwd", action="store", default="pi-server-pwd",
                    help="PI Server user login password")
parser.add_argument("--asset-name", action="store", default="asset-name",
                    help="Asset name")
args = vars(parser.parse_args())

pi_host = args["pi_host"]
pi_admin = args["pi_admin"]
pi_passwd = args["pi_passwd"]
pi_db = args["pi_db"]
asset_name = args["asset_name"]


def read_data_from_pi_web_api(host, admin, password, pi_database, af_hierarchy_list, asset, sensor):
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
    # List of elements
    url_elements_data_list = None

    username_password = "{}:{}".format(admin, password)
    username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
    headers = {'Authorization': 'Basic %s' % username_password_b64}

    try:
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

        # This block is for iteration when we have multi-level hierarchy.
        # For example, if we have DefaultAFLocation as "fledge/room1/machine1" then
        # it will recursively find elements of "fledge" and then "room1".
        # And next block is for finding element of "machine1".

        af_level_count = 0
        for level in af_hierarchy_list[:-1]:
            if url_elements_list is not None:
                conn.request("GET", url_elements_list, headers=headers)
                res = conn.getresponse()
                r = json.loads(res.read().decode())
                for el in r["Items"]:
                    if el["Name"] == af_hierarchy_list[af_level_count]:
                        url_elements_list = el["Links"]["Elements"]
                        if af_level_count == 0:
                            web_id_root = el["WebId"]
                        af_level_count = af_level_count + 1

        if url_elements_list is not None:
            conn.request("GET", url_elements_list, headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            items = r["Items"]
            for el in items:
                if el["Name"] == af_hierarchy_list[-1]:
                    url_elements_data_list = el["Links"]["Elements"]

        if url_elements_data_list is not None:
            conn.request("GET", url_elements_data_list, headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            items = r["Items"]
            for el2 in items:
                if el2["Name"] == asset:
                    url_recorded_data = el2["Links"]["RecordedData"]
                    web_id = el2["WebId"]

        _data_pi = {}
        if url_recorded_data is not None:
            conn.request("GET", url_recorded_data, headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            _items = r["Items"]
            for el in _items:
                _recoded_value_list = []
                for _head in sensor:
                    # This checks if the recorded datapoint is present in the items that we retrieve from the PI server.
                    if _head in el["Name"]:
                        elx = el["Items"]
                        for _el in elx:
                            _recoded_value_list.append(_el["Value"])
                        _data_pi[_head] = _recoded_value_list

            # Delete recorded elements
            conn.request("DELETE", '/piwebapi/elements/{}'.format(web_id_root), headers=headers)
            res = conn.getresponse()
            res.read()

            return _data_pi
    except (KeyError, IndexError, Exception):
        return None


af_hierarchy_level = "fledge/data_piwebapi/default"
af_hierarchy_level_list = af_hierarchy_level.split("/")
type_id = 1
recorded_datapoint = "{}measurement_{}".format(type_id, asset_name)
# Name of asset in the PI server
pi_asset_name = "{}-type{}".format(asset_name, type_id)

while (data_from_pi is None or data_from_pi == []) and retry_count < retries:
    data_from_pi = read_data_from_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, af_hierarchy_level_list,
                                             pi_asset_name, {recorded_datapoint})
    retry_count += 1
    time.sleep(wait_time * 2)

if data_from_pi is None or retry_count == retries:
    assert False, "Failed to read data from PI"
