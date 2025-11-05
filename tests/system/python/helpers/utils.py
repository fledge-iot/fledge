# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

from datetime import datetime
import os

import http.client
import json

"""Utility methods"""


def serialize_stats_map(jdoc):
    actual_stats_map = {}
    for itm in jdoc:
        actual_stats_map[itm['key']] = itm['value']
    return actual_stats_map


def get_asset_tracking_details(fledge_url, event=None):
    _connection = http.client.HTTPConnection(fledge_url)
    uri = '/fledge/track'
    if event:
        uri += '?event={}'.format(event)
    _connection.request("GET", uri)
    r = _connection.getresponse()
    assert 200 == r.status
    r = r.read().decode()
    jdoc = json.loads(r)
    return jdoc


def post_request(fledge_url, post_url, payload):
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("POST", post_url, json.dumps(payload))
    res = conn.getresponse()
    assert 200 == res.status, "ERROR! POST {} request failed".format(post_url)
    res = res.read().decode()
    r = json.loads(res)
    return r


def get_request(fledge_url, get_url):
    con = http.client.HTTPConnection(fledge_url)
    con.request("GET", get_url)
    res = con.getresponse()
    assert 200 == res.status, "ERROR! GET {} request failed".format(get_url)
    r = json.loads(res.read().decode())
    return r


def put_request(fledge_url, put_url, payload = None):
    conn = http.client.HTTPConnection(fledge_url)
    conn.request("PUT", put_url, json.dumps(payload))
    res = conn.getresponse()
    assert 200 == res.status, "ERROR! PUT {} request failed".format(put_url)
    r = json.loads(res.read().decode())
    return r


def delete_request(fledge_url, delete_url):
    con = http.client.HTTPConnection(fledge_url)
    con.request("DELETE", delete_url)
    res = con.getresponse()
    assert 200 == res.status, "ERROR! GET {} request failed".format(delete_url)
    r = json.loads(res.read().decode())
    return r


def validate_date_format(datetime_str, format_str=None):
    """
    Check if the given datetime string matches the specified format

    Parameters:
    - datetime_str: The datetime string to check.
    - format_str: The format string that the datetime string should match. By default, format '%Y-%m-%d %H:%M:%S.%f'

    Returns:
    - True if the string matches the format, False otherwise.
    """
    try:
        if format_str is None:
            format_str = "%Y-%m-%d %H:%M:%S.%f"
        datetime.strptime(datetime_str, format_str)
        return True
    except ValueError:
        return False


def detect_os():
    """
    Detect Ubuntu or Raspberry Pi OS version
    
    Returns:
    - str: 'Ubuntu X' where X is the major version (e.g., 'Ubuntu 20', 'Ubuntu 22')
    - str: Codename for Raspberry Pi OS (e.g., 'Bookworm', 'Bullseye')
    - str: 'Unknown' if neither Ubuntu nor Raspberry Pi OS is detected
    """
    try:
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                content = f.read()
                
                # Parse the content into a dictionary
                os_info = {}
                for line in content.split('\n'):
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        os_info[key] = value.strip().strip('"')
                
                # Check for Ubuntu
                if 'Ubuntu' in content:
                    version_id = os_info.get('VERSION_ID', '')
                    major_version = version_id.split('.')[0]
                    return f'Ubuntu {major_version}'
                
                # Check for Raspberry Pi OS (Debian-based)
                elif os_info.get('ID') == 'debian' and os_info.get('VERSION_CODENAME') in ['bullseye', 'bookworm']:
                    codename = os_info.get('VERSION_CODENAME', '')
                    return codename.capitalize()
        
        return 'Unknown'
    
    except Exception:
        return 'Unknown'

