# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import os
from aiohttp import web
from foglamp.services.core import connect
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.common.common import _FOGLAMP_ROOT, _FOGLAMP_DATA

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    -------------------------------------------------------------------------------
    | GET POST         | /foglamp/certificate                                     |
    | DELETE           | /foglamp/certificate/{name}                              |
    -------------------------------------------------------------------------------
"""


async def get_certs(request):
    """ Get the list of certs

    :Example:
        curl -X GET http://localhost:8081/foglamp/certificate
    """
    certs_dir = _get_certs_dir('/etc/certs')
    certs = []
    keys = []
    key_valid_extensions = ('.key', '.pem')
    for root, dirs, files in os.walk(certs_dir):
        if root.endswith('json'):
            for f in files:
                if f.endswith('.json'):
                    certs.append(f)
                    files.remove(f)
        if root.endswith('pem'):
            for f in files:
                if f.endswith('.pem'):
                    certs.append(f)
                    files.remove(f)
        for f in files:
            if f.endswith('.cert'):
                certs.append(f)
            if f.endswith(key_valid_extensions):
                keys.append(f)
    return web.json_response({"certs": certs, "keys": keys})


async def upload(request):
    """ Upload a certificate

    :Example:
        curl -F "cert=@filename.pem" http://localhost:8081/foglamp/certificate
        curl -F "cert=@filename.json" http://localhost:8081/foglamp/certificate
        curl -F "key=@filename.pem" -F "cert=@filename.pem" http://localhost:8081/foglamp/certificate
        curl -F "key=@filename.key" -F "cert=@filename.json" http://localhost:8081/foglamp/certificate
        curl -F "key=@filename.key" -F "cert=@filename.cert" http://localhost:8081/foglamp/certificate
        curl -F "key=@filename.key" -F "cert=@filename.cert" -F "overwrite=1" http://localhost:8081/foglamp/certificate
    """
    data = await request.post()
    # contains the name of the file in string format
    key_file = data.get('key')
    cert_file = data.get('cert')
    allow_overwrite = data.get('overwrite', '0')

    # accepted values for overwrite are '0 and 1'
    if allow_overwrite in ('0', '1'):
        should_overwrite = True if int(allow_overwrite) == 1 else False
    else:
        raise web.HTTPBadRequest(reason="Accepted value for overwrite is 0 or 1")

    if not cert_file:
        raise web.HTTPBadRequest(reason="Cert file is missing")

    cert_filename = cert_file.filename
    if cert_filename.endswith('.cert'):
        if not key_file:
            raise web.HTTPBadRequest(reason="key file is missing, or upload certificate with .pem or .json extension")

    cert_valid_extensions = ('.cert', '.json', '.pem')
    key_valid_extensions = ('.key', '.pem')
    key_filename = None
    if key_file:
        key_filename = key_file.filename
        if not key_filename.endswith(key_valid_extensions):
            raise web.HTTPBadRequest(reason="Accepted file extensions are .key and .pem for key file")

    if not cert_filename.endswith(cert_valid_extensions):
        raise web.HTTPBadRequest(reason="Accepted file extensions are .cert, .json and .pem for cert file")

    certs_dir = _get_certs_dir('/etc/certs/')
    if cert_filename.endswith('.pem'):
        certs_dir = _get_certs_dir('/etc/certs/pem')
    if cert_filename.endswith('.json'):
        certs_dir = _get_certs_dir('/etc/certs/json')

    found_files = _find_file(cert_filename, certs_dir)
    is_found = True if len(found_files) else False
    if is_found and should_overwrite is False:
        raise web.HTTPBadRequest(reason="Certificate with the same name already exists. "
                                        "To overwrite set the overwrite to 1")
    if key_file:
        found_files = _find_file(key_filename, certs_dir)
        is_found = True if len(found_files) else False
        if is_found and should_overwrite is False:
            raise web.HTTPBadRequest(reason="Key cert with the same name already exists. "
                                            "To overwrite set the overwrite to 1")
    if cert_file:
        cert_file_data = data['cert'].file
        cert_file_content = cert_file_data.read()
        cert_file_path = str(certs_dir) + '/{}'.format(cert_filename)
        with open(cert_file_path, 'wb') as f:
            f.write(cert_file_content)
    if key_file:
        key_file_data = data['key'].file
        key_file_content = key_file_data.read()
        key_file_path = str(certs_dir) + '/{}'.format(key_filename)
        with open(key_file_path, 'wb') as f:
            f.write(key_file_content)

    # in order to bring this new cert usage into effect, make sure to
    # update config for category rest_api
    # and reboot
    msg = "{} has been uploaded successfully".format(cert_filename)
    if key_file:
        msg = "{} and {} have been uploaded successfully".format(key_filename, cert_filename)
    return web.json_response({"result": msg})


async def delete_certificate(request):
    """ Delete a certificate

    :Example:
          curl -X DELETE http://localhost:8081/foglamp/certificate/foglamp.pem
          curl -X DELETE http://localhost:8081/foglamp/certificate/foglamp.cert
          curl -X DELETE http://localhost:8081/foglamp/certificate/foglamp.json?type=cert
          curl -X DELETE http://localhost:8081/foglamp/certificate/foglamp.pem?type=cert
          curl -X DELETE http://localhost:8081/foglamp/certificate/foglamp.key
          curl -X DELETE http://localhost:8081/foglamp/certificate/foglamp.pem?type=key
    """
    cert_name = request.match_info.get('name', None)
    valid_extensions = ('.cert', '.json', '.key', '.pem')
    if not cert_name.endswith(valid_extensions):
        raise web.HTTPBadRequest(reason="Accepted file extensions are {}".format(valid_extensions))

    certs_dir = _get_certs_dir('/etc/certs/')
    is_found = False
    dir_path = [certs_dir + cert_name]
    if 'type' in request.query and request.query['type'] != '':
        _type = request.query['type']
        if _type not in ['cert', 'key']:
            raise web.HTTPBadRequest(reason="Only cert and key are allowed for the value of type param")
        if _type == 'cert':
            if not cert_name.endswith('.cert'):
                if os.path.isfile(certs_dir + 'pem/' + cert_name):
                    is_found = True
                    dir_path = [certs_dir + 'pem/' + cert_name]
                if os.path.isfile(certs_dir + 'json/' + cert_name):
                    is_found = True
                    dir_path = [certs_dir + 'json/' + cert_name]
            else:
                if os.path.isfile(certs_dir + cert_name):
                    is_found = True
                else:
                    is_found = False
        else:
            if os.path.isfile(certs_dir + cert_name):
                is_found = True
            else:
                is_found = False

    if 'type' not in request.query:
        for root, dirs, files in os.walk(certs_dir):
            if root.endswith('json'):
                for f in files:
                    if cert_name == f:
                        is_found = True
                        dir_path.append(certs_dir + 'json/' + cert_name)
                        files.remove(f)
            if root.endswith('pem'):
                for f in files:
                    if cert_name == f:
                        is_found = True
                        dir_path.append(certs_dir + 'pem/' + cert_name)
                        files.remove(f)
            for f in files:
                if cert_name == f:
                    is_found = True

    if not is_found:
        raise web.HTTPNotFound(reason='Certificate with name {} does not exist'.format(cert_name))

    # read config
    # if cert_name is currently set for 'certificateName' in config for 'rest_api'
    cf_mgr = ConfigurationManager(connect.get_storage_async())
    result = await cf_mgr.get_category_item(category_name='rest_api', item_name='certificateName')
    if cert_name.split('.')[0] == result['value']:
        raise web.HTTPConflict(reason='Certificate with name {} is already in use, you can not delete'
                               .format(cert_name))

    # Remove file
    for fp in dir_path:
        os.remove(fp)
    return web.json_response({'result': "{} has been deleted successfully".format(cert_name)})


def _get_certs_dir(_path):
    dir_path = _FOGLAMP_DATA + _path if _FOGLAMP_DATA else _FOGLAMP_ROOT + '/data' + _path
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    certs_dir = os.path.expanduser(dir_path)
    return certs_dir


def _find_file(name, path):
    result = []
    for root, dirs, files in os.walk(path):
        if name in files:
            result.append(os.path.join(root, name))

    return result
