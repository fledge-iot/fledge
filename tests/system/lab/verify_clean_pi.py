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


def delete_pi_point(host, admin, password, asset_name, data_point_name):
    """Deletes a given pi point fromPI."""
    username_password = "{}:{}".format(admin, password)

    username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
    headers = {'Authorization': 'Basic %s' % username_password_b64, 'Content-Type': 'application/json'}

    try:
        web_id, pi_point_name = search_for_pi_point(host, admin, password, asset_name, data_point_name)
        if not web_id:
            print("Could not search PI Point {}. ".format(data_point_name))
            return

        conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
        conn.request("DELETE", "/piwebapi/points/{}".format(web_id), headers=headers)
        r = conn.getresponse()
        assert r.status == 204, "Could not delete" \
                                " the pi point {}.".format(pi_point_name)

        conn.close()

    except Exception as er:
        print("Could not delete pi point {} due to {}".format(data_point_name, er))
        assert False, "Could not delete pi point {} due to {}".format(data_point_name, er)


def search_for_pi_point(host, admin, password, asset_name, data_point_name):
    """Searches for a pi point in PI return its web_id and its full name in PI."""
    username_password = "{}:{}".format(admin, password)

    username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
    headers = {'Authorization': 'Basic %s' % username_password_b64, 'Content-Type': 'application/json'}
    try:
        conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
        conn.request("GET", '/piwebapi/dataservers', headers=headers)
        res = conn.getresponse()
        r = json.loads(res.read().decode())
        points_url = r["Items"][0]["Links"]["Points"]
    except Exception:
        assert False, "Could not request data server of PI"

    try:
        conn.request("GET", points_url, headers=headers)
        res = conn.getresponse()
        points = json.loads(res.read().decode())
    except Exception:
        assert False, "Could not get Points data."

    name_to_search = asset_name + '.' + data_point_name
    for single_point in points['Items']:

        if name_to_search in single_point['Name']:
            web_id = single_point['WebId']
            pi_point_name = single_point["Name"]
            conn.close()
            return web_id, pi_point_name

    return None, None


def search_for_element_template(host, admin, password, pi_database, search_string):
    """Searches for an element template using a search string. If found returns its web_id.
       If multiple templates found then returns an array of web_ids.
    """
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
                    element_template_list = el["Links"]["ElementTemplates"]

        web_ids = []
        if element_template_list is not None:
            conn.request("GET", element_template_list, headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())
            for template_info in r['Items']:
                if search_string in template_info['Name']:
                    web_ids.append(template_info['WebId'])

        if not web_ids:
            print("Could not find asset template with name {}".format(search_string))
            return []
        return web_ids

    except Exception as er:
        print("Could not find asset element template with name"
              "  {} due to {}".format(search_string, er))
        return []


def delete_element_template(host, admin, password, web_id):
    """Deletes an element template through its web_id."""
    username_password = "{}:{}".format(admin, password)

    username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
    headers = {'Authorization': 'Basic %s' % username_password_b64, 'Content-Type': 'application/json'}

    try:

        conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
        conn.request("DELETE", "/piwebapi/elementtemplates/{}".format(web_id), headers=headers)
        r = conn.getresponse()
        assert r.status == 204, "Could not delete" \
                                " element template for web_id {}.".format(web_id)

        conn.close()

    except Exception as er:
        print("Could not delete element template {} due to {}".format(web_id, er))
        assert False, "Could not delete element template {} due to {}".format(web_id, er)


def delete_element_hierarchy(host, admin, password, pi_database, af_hierarchy_list):
    """ This method deletes the given hierarchy list form PI."""
    url_elements_list = None

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

        if web_id_root:
            conn.request("DELETE", '/piwebapi/elements/{}'.format(web_id_root), headers=headers)
            r = conn.getresponse()
            assert r.status == 204, "Could not delete element hierarchy of {}".format(af_hierarchy_list)
            conn.close()

    except Exception as er:
        print("Could not delete hierarchy of {} due to {}".format(af_hierarchy_list, er))
        print("Most probably it does not exist.")


def clear_cache(host, admin, password, pi_database):
    """Method that deletes cache by supplying 'Cache-Control': 'no-cache' in header of GET request for
        element list.
    """
    username_password = "{}:{}".format(admin, password)
    username_password_b64 = base64.b64encode(username_password.encode('ascii')).decode("ascii")
    headers = {'Authorization': 'Basic %s' % username_password_b64, 'Cache-Control': 'no-cache'}
    normal_header = {'Authorization': 'Basic %s' % username_password_b64}
    try:
        conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
        conn.request("GET", '/piwebapi/assetservers', headers=normal_header)
        res = conn.getresponse()
        assert res.status == 200, "Could not request asset server of Pi Web API."
        r = json.loads(res.read().decode())
        dbs = r["Items"][0]["Links"]["Databases"]

        if dbs is not None:
            conn.request("GET", dbs, headers=normal_header)
            res = conn.getresponse()
            assert res.status == 200, "Databases is not accessible."
            r = json.loads(res.read().decode())
            for el in r["Items"]:
                if el["Name"] == pi_database:
                    url_elements_list = el["Links"]["Elements"]

        print("Getting old cache")
        conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
        conn.request("GET", '/piwebapi/system/cacheinstances', headers=normal_header)
        res = conn.getresponse()
        r = json.loads(res.read().decode())
        try:
            # assuming we have single user Administrator
            old_cache_refresh_time = r["Items"][0]['LastRefreshTime']
        except (IndexError, KeyError):
            print("The cache does not exist. ")
            return

        print("Old cache refresh time {} ".format(old_cache_refresh_time))
        conn.close()

        print("Going to request element list with cache control no cache.")
        if url_elements_list is not None:
            conn.request("GET", url_elements_list, headers=headers)
            res = conn.getresponse()
            r = json.loads(res.read().decode())

        conn.close()

        # for verification whether we are able to clear cache.
        print("Now verifying whether cache cleared.")
        conn = http.client.HTTPSConnection(host, context=ssl._create_unverified_context())
        conn.request("GET", '/piwebapi/system/cacheinstances', headers=normal_header)
        res = conn.getresponse()
        r = json.loads(res.read().decode())
        try:
            # assuming we have only one user named Administrator.
            new_cache_refresh_time = r["Items"][0]['LastRefreshTime']
        except (KeyError, IndexError):
            print("The cache does not exist.")
            return

        print("New cache refresh time {} ".format(new_cache_refresh_time))
        conn.close()

        assert new_cache_refresh_time != old_cache_refresh_time, "The cache has not been refreshed."

    except Exception as er:
        print("Could not clear cache due to {}".format(er))
        return


def _clear_pi_system_through_pi_web_api(host, admin, password, pi_database, af_hierarchy_list, asset_dict):
    """
       Clears the pi system through pi web API.
       1. Deletes the elements.
       2. Deletes element templates.
       3. Deletes the PI Points.
       4. Clears the cache.
    Args:
        host (str): The address of the pi server.
        admin (str): The user name inside pi server.
        password (str): The passowrd for the username used above.
        pi_database (str): The database inside pi server.
        af_hierarchy_list (list): The asset heirarchy list to delete.
        asset_dict (dict): It's a dict where keys are asset names, and it's value is list where each
                           element of list is a datapoint associated with that asset.

    Returns:
        None
    """
    print("Going to delete the element hierarchy list {}.".format(af_hierarchy_list))
    delete_element_hierarchy(host, admin, password, pi_database, af_hierarchy_list)
    print("Deleted the element hierarchy list {}.".format(af_hierarchy_list))

    for asst_name in asset_dict.keys():
        for dp_name in asset_dict[asset_name]:
            print("Going to delete the PI point. with name {}.{}".format(asst_name, dp_name))
            delete_pi_point(host, admin, password, asset_name, dp_name)
            print("Deleted the PI point. with name {}.{}".format(asst_name, dp_name))

    for h_level in af_hierarchy_list:
        web_ids = search_for_element_template(host, admin, password, pi_database, h_level)
        print("Going to delete the element template with name {} and web ids {}".format(h_level, web_ids))
        for web_id in web_ids:
            delete_element_template(host, admin, password, web_id)
        print("Deleted the element template with name {} and web ids {}".format(h_level, web_ids))

    clear_cache(host, admin, password, pi_database)
    print("Cleared the cache of Pi system.")


pi_host = args["pi_host"]
pi_admin = args["pi_admin"]
pi_passwd = args["pi_passwd"]
pi_db = args["pi_db"]
asset_name = args["asset_name"]

af_hierarchy_level = "fledge/data_piwebapi/default"
af_hierarchy_level_list = af_hierarchy_level.split("/")

_clear_pi_system_through_pi_web_api(pi_host, pi_admin, pi_passwd, pi_db, af_hierarchy_level_list,
                                    {asset_name: [asset_name]})
