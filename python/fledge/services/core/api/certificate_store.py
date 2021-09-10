# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import os
import json

from aiohttp import web

from fledge.common import logger
from fledge.common.web.middleware import has_permission
from fledge.services.core import connect
from fledge.common.configuration_manager import ConfigurationManager
from fledge.common.common import _FLEDGE_ROOT, _FLEDGE_DATA

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_help = """
    -------------------------------------------------------------------------------
    | GET POST         | /fledge/certificate                                     |
    | DELETE           | /fledge/certificate/{name}                              |
    -------------------------------------------------------------------------------
"""
FORBIDDEN_MSG = 'Resource you were trying to reach is absolutely forbidden for some reason'
_logger = logger.setup(__name__)


async def get_certs(request):
    """ Get the list of certs

    :Example:
        curl -X GET http://localhost:8081/fledge/certificate
    """
    certs = []
    keys = []

    key_valid_extensions = ('.key', '.pem')
    short_cert_name_valid_extensions = ('.cert', '.cer', '.csr', '.crl', '.crt', '.der', '.p12', '.pfx')
    certs_root_dir = _get_certs_dir('/etc/certs')
    for root, dirs, files in os.walk(certs_root_dir):
        if not root.endswith(("pem", "json")):
            for f in files:
                if f.endswith(short_cert_name_valid_extensions):
                    certs.append(f)
                if f.endswith(key_valid_extensions):
                    keys.append(f)

    json_certs_path = _get_certs_dir('/etc/certs/json')
    json_cert_files = os.listdir(json_certs_path)
    json_certs = [f for f in json_cert_files if f.endswith('.json')]
    certs += json_certs

    pem_certs_path = _get_certs_dir('/etc/certs/pem')
    pem_cert_files = os.listdir(pem_certs_path)
    pem_certs = [f for f in pem_cert_files if f.endswith('.pem')]
    certs += pem_certs

    return web.json_response({"certs": certs, "keys": keys})


async def upload(request):
    """ Upload a certificate

    :Example:
        curl -F "cert=@filename.pem" http://localhost:8081/fledge/certificate
        curl -F "cert=@filename.json" http://localhost:8081/fledge/certificate
        curl -F "key=@filename.pem" -F "cert=@filename.pem" http://localhost:8081/fledge/certificate
        curl -F "key=@filename.key" -F "cert=@filename.json" http://localhost:8081/fledge/certificate
        curl -F "key=@filename.key" -F "cert=@filename.cert" http://localhost:8081/fledge/certificate
        curl -F "cert=@filename.cert" http://localhost:8081/fledge/certificate
        curl -F "cert=@filename.cer" http://localhost:8081/fledge/certificate
        curl -F "cert=@filename.csr" http://localhost:8081/fledge/certificate
        curl -F "cert=@filename.crl" http://localhost:8081/fledge/certificate
        curl -F "cert=@filename.crt" http://localhost:8081/fledge/certificate
        curl -F "cert=@filename.der" http://localhost:8081/fledge/certificate
        curl -F "cert=@filename.p12" http://localhost:8081/fledge/certificate
        curl -F "cert=@filename.pfx" http://localhost:8081/fledge/certificate
        curl -F "key=@filename.key" -F "cert=@filename.cert" -F "overwrite=1" http://localhost:8081/fledge/certificate
    """
    data = await request.post()
    # contains the name of the file in string format
    key_file = data.get('key')
    cert_file = data.get('cert')
    allow_overwrite = data.get('overwrite', '0')
    # accepted values for overwrite are '0 and 1'
    should_overwrite = False
    if allow_overwrite in ('0', '1'):
        should_overwrite = True if int(allow_overwrite) == 1 else False
    else:
        raise web.HTTPBadRequest(reason="Accepted value for overwrite is 0 or 1")
    
    if not cert_file:
        raise web.HTTPBadRequest(reason="Cert file is missing")

    cert_filename = cert_file.filename

    # default installed auth cert keys can be deleted, for matching/debugging disallow overwrite
    if cert_filename in ['admin.cert', 'admin.key', 'user.cert', 'user.key', 'fledge.key', 'fledge.cert', 'ca.key',
                         'ca.cert']:
        if request.is_auth_optional:
            _logger.warning(FORBIDDEN_MSG)
            raise web.HTTPForbidden(reason=FORBIDDEN_MSG, body=json.dumps({"message": FORBIDDEN_MSG}))
        else:
            if not request.user_is_admin:
                msg = "admin role permissions required to overwrite the default installed auth/TLS certificates."
                _logger.warning(msg)
                raise web.HTTPForbidden(reason=msg, body=json.dumps({"message": msg}))
    # note.. We are not checking if HTTPS enabled or auth mechanism?
    # Here, in secured instance, we are simply disallowing non-admin user to overwrite/import configured TLS/CA certificates
    if request.user and not request.user_is_admin:
        cf_mgr = ConfigurationManager(connect.get_storage_async())
        cat = await cf_mgr.get_category_all_items(category_name='rest_api')
        configured_ca_and_tls_certs = [cat['certificateName']['value'], cat['authCertificateName']['value']]
        if cert_filename and cert_filename.rpartition('.')[0] in configured_ca_and_tls_certs:  # we better disallow any extension with those names instead of [1]/endswith .cert
            msg = 'Certificate with name {} is configured to be used, ' \
                  'An `admin` role permissions required to add/overwrite.'.format(cert_filename)
            _logger.warning(msg)
            raise web.HTTPForbidden(reason=msg, body=json.dumps({"message": msg}))

    key_valid_extensions = ('.key', '.pem')
    cert_valid_extensions = ('.cert', '.cer', '.csr', '.crl', '.crt', '.der', '.json', '.pem', '.p12', '.pfx')

    key_filename = None
    if key_file:
        key_filename = key_file.filename
        if not key_filename.endswith(key_valid_extensions):
            raise web.HTTPBadRequest(reason="Accepted file extensions are {} for key file".format(key_valid_extensions))

    if not cert_filename.endswith(cert_valid_extensions):
        raise web.HTTPBadRequest(reason="Accepted file extensions are {} for cert file".format(cert_valid_extensions))

    certs_dir = _get_certs_dir('/etc/certs/')
    if cert_filename.endswith('.pem'):
        certs_dir = _get_certs_dir('/etc/certs/pem')
    if cert_filename.endswith('.json'):
        certs_dir = _get_certs_dir('/etc/certs/json')

    is_found = True if len(_find_file(cert_filename, certs_dir)) else False
    if is_found and should_overwrite is False:
        raise web.HTTPBadRequest(reason="Certificate with the same name already exists! "
                                        "To overwrite, set the overwrite flag")
    if key_file:
        key_file_found = True if len(_find_file(key_filename, _get_certs_dir('/etc/certs/'))) else False
        if key_file_found and should_overwrite is False:
            raise web.HTTPBadRequest(reason="Key cert with the same name already exists. "
                                            "To overwrite, set the overwrite flag")
    if cert_file:
        cert_file_data = data['cert'].file
        cert_file_content = cert_file_data.read()
        cert_file_path = str(certs_dir) + '/{}'.format(cert_filename)
        with open(cert_file_path, 'wb') as f:
            f.write(cert_file_content)
    if key_file:
        key_file_data = data['key'].file
        key_file_content = key_file_data.read()
        key_file_path = str(_get_certs_dir('/etc/certs/')) + '/{}'.format(key_filename)
        with open(key_file_path, 'wb') as f:
            f.write(key_file_content)

    # in order to bring this new cert usage into effect, make sure to
    # update config for category rest_api
    # and restart for TLS
    msg = "{} has been uploaded successfully".format(cert_filename)
    if key_file:
        msg = "{} and {} have been uploaded successfully".format(key_filename, cert_filename)
    return web.json_response({"result": msg})


@has_permission("admin")
async def delete_certificate(request):
    """ Delete a certificate

    :Example:
          curl -X DELETE http://localhost:8081/fledge/certificate/user.key
          curl -X DELETE http://localhost:8081/fledge/certificate/user.cert
          curl -X DELETE http://localhost:8081/fledge/certificate/filename.cer
          curl -X DELETE http://localhost:8081/fledge/certificate/filename.csr
          curl -X DELETE http://localhost:8081/fledge/certificate/filename.crl
          curl -X DELETE http://localhost:8081/fledge/certificate/filename.crt
          curl -sX DELETE http://localhost:8081/fledge/certificate/filename.der
          curl -X DELETE http://localhost:8081/fledge/certificate/filename.p12
          curl -X DELETE http://localhost:8081/fledge/certificate/filename.pfx
          curl -X DELETE http://localhost:8081/fledge/certificate/fledge.json?type=cert
          curl -X DELETE http://localhost:8081/fledge/certificate/fledge.pem?type=cert
          curl -X DELETE http://localhost:8081/fledge/certificate/fledge.pem
          curl -X DELETE http://localhost:8081/fledge/certificate/fledge.pem?type=key
    """
    file_name = request.match_info.get('name', None)
    valid_extensions = ('.cert', '.cer', '.csr', '.crl', '.crt', '.der', '.json', '.key', '.pem', '.p12', '.pfx')

    if not file_name.endswith(valid_extensions):
        msg = "Accepted file extensions are {}".format(valid_extensions)
        raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))
    if file_name in ['admin.cert', 'user.cert', 'fledge.key', 'fledge.cert', 'ca.key', 'ca.cert']:
        if request.is_auth_optional:
            _logger.warning(FORBIDDEN_MSG)
            raise web.HTTPForbidden(reason=FORBIDDEN_MSG, body=json.dumps({"message": FORBIDDEN_MSG}))
    
    cf_mgr = ConfigurationManager(connect.get_storage_async())
    cat = await cf_mgr.get_category_all_items(category_name='rest_api')
    configured_ca_and_tls_certs = [cat['certificateName']['value'], cat['authCertificateName']['value']]
    if file_name and file_name.rpartition('.')[0] in configured_ca_and_tls_certs:
        # check if cert_name is currently set for 'certificateName' or authCertificateName in config for 'rest_api'
        msg = 'Certificate with name {} is configured for use, you can not delete but overwrite if required.'.format(
            file_name)
        raise web.HTTPConflict(reason=msg, body=json.dumps({"message": msg}))

    _type = None
    if 'type' in request.query and request.query['type'] != '':
        _type = request.query['type']
        if _type not in ['cert', 'key']:
            msg = "Only cert and key are allowed for the value of type param"
            raise web.HTTPBadRequest(reason=msg, body=json.dumps({"message": msg}))

    certs_dir = _get_certs_dir('/etc/certs/')
    is_found = False
    cert_path = list()

    if _type and _type == 'cert':
        short_cert_name_valid_extensions = ('.cert', '.cer', '.csr', '.crl', '.crt', '.der', '.p12', '.pfx')
        if not file_name.endswith(short_cert_name_valid_extensions):
            if os.path.isfile(certs_dir + 'pem/' + file_name):
                is_found = True
                cert_path = [certs_dir + 'pem/' + file_name]
            if os.path.isfile(certs_dir + 'json/' + file_name):
                is_found = True
                cert_path = [certs_dir + 'json/' + file_name]
        else:
            if os.path.isfile(certs_dir + file_name):
                is_found = True
                cert_path = [certs_dir + file_name]

    if _type and _type == 'key':
        if os.path.isfile(certs_dir + file_name):
            is_found = True
            cert_path = [certs_dir + file_name]

    if _type is None:
        for root, dirs, files in os.walk(certs_dir):
            if root.endswith('json'):
                for f in files:
                    if file_name == f:
                        is_found = True
                        cert_path.append(certs_dir + 'json/' + file_name)
                        files.remove(f)
            if root.endswith('pem'):
                for f in files:
                    if file_name == f:
                        is_found = True
                        cert_path.append(certs_dir + 'pem/' + file_name)
                        files.remove(f)
            for f in files:
                if file_name == f:
                    is_found = True
                    cert_path.append(certs_dir + file_name)

    if not is_found:
        msg = 'Certificate with name {} does not exist'.format(file_name)
        raise web.HTTPNotFound(reason=msg, body=json.dumps({"message": msg}))

    # Remove file
    for fp in cert_path:
        os.remove(fp)
    return web.json_response({'result': "{} has been deleted successfully".format(file_name)})


def _get_certs_dir(_path):
    dir_path = _FLEDGE_DATA + _path if _FLEDGE_DATA else _FLEDGE_ROOT + '/data' + _path
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    certs_dir = os.path.expanduser(dir_path)
    return certs_dir


def _find_file(name, path):
    fl = list()
    for root, dirs, files in os.walk(path):
        if name in files:
            fl.append(os.path.join(root, name))
    return fl
