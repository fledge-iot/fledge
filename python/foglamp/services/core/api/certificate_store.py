# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import os
from aiohttp import web
from foglamp.services.core import connect
from foglamp.common.configuration_manager import ConfigurationManager

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_FOGLAMP_DATA = os.getenv("FOGLAMP_DATA", default=None)
_FOGLAMP_ROOT = os.getenv("FOGLAMP_ROOT", default='/usr/local/foglamp')


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

    # Get certs directory path
    certs_dir = _get_certs_dir()
    total_files = []
    valid_extensions = ('.key', '.cert')

    for root, dirs, files in os.walk(certs_dir):
        total_files = [f for f in files if f.endswith(valid_extensions)]

    # Get filenames without extension
    file_names = [os.path.splitext(fname)[0] for fname in total_files]

    # Get unique list from file_names
    unique_list = list(set(file_names))

    def search_file(fname):
        # Search file with extension, if found then filename with extension else empty
        if fname in total_files:
            return fname
        return ''

    certs = []
    for fname in unique_list:
        cert_pair = {'key': search_file('{}.key'.format(fname)),
                     'cert': search_file('{}.cert'.format(fname))}
        certs.append(cert_pair)

    return web.json_response({"certificates": certs})


async def upload(request):
    """ Upload a certificate

    :Example:
        curl -F "key=@filename.key" -F "cert=@filename.cert" http://localhost:8081/foglamp/certificate
        curl -F "key=@filename.key" -F "cert=@filename.cert" -F "overwrite=1" http://localhost:8081/foglamp/certificate
    """
    data = await request.post()

    # contains the name of the file in string format
    key_file = data.get('key')
    cert_file = data.get('cert')

    # accepted values for overwrite are '0 and 1'
    allow_overwrite = data.get('overwrite', '0')
    if allow_overwrite in ('0', '1'):
        should_overwrite = True if int(allow_overwrite) == 1 else False
    else:
        raise web.HTTPBadRequest(reason="Accepted value for overwrite is 0 or 1")

    if not key_file or not cert_file:
        raise web.HTTPBadRequest(reason="key or certs file is missing")

    key_filename = key_file.filename
    cert_filename = cert_file.filename

    # accepted extensions are '.key and .cert'
    valid_extensions = ('.key', '.cert')
    if not cert_filename.endswith(valid_extensions) or not key_filename.endswith(valid_extensions):
        raise web.HTTPBadRequest(reason="Accepted file extensions are .key and .cert")

    # certs and key filename should match
    if cert_filename and key_filename:
        if cert_filename.split(".")[0] != key_filename.split(".")[0]:
            raise web.HTTPBadRequest(reason="key and certs file name should match")

    # Get certs directory path
    certs_dir = _get_certs_dir()
    found_files = _find_file(cert_filename, certs_dir)
    is_found = True if len(found_files) else False
    if is_found and should_overwrite is False:
        raise web.HTTPBadRequest(reason="Certificate with the same name already exists. "
                                        "To overwrite set the overwrite to 1")

    if key_file:
        key_file_data = data['key'].file
        key_file_content = key_file_data.read()
        key_file_path = str(certs_dir) + '/{}'.format(key_filename)
        with open(key_file_path, 'wb') as f:
            f.write(key_file_content)

    if cert_file:
        cert_file_data = data['cert'].file
        cert_file_content = cert_file_data.read()
        cert_file_path = str(certs_dir) + '/{}'.format(cert_filename)
        with open(cert_file_path, 'wb') as f:
            f.write(cert_file_content)

    # in order to bring this new cert usage into effect, make sure to
    # update config for category rest_api
    # and reboot
    return web.json_response({"result": "{} and {} have been uploaded successfully"
                             .format(key_filename, cert_filename)})


async def delete_certificate(request):
    """ Delete a certificate

    :Example:
          curl -X DELETE http://localhost:8081/foglamp/certificate/foglamp
    """
    cert_name = request.match_info.get('name', None)

    certs_dir = _get_certs_dir()
    cert_file = certs_dir + '/{}.cert'.format(cert_name)
    key_file = certs_dir + '/{}.key'.format(cert_name)

    if not os.path.isfile(cert_file) and not os.path.isfile(key_file):
        raise web.HTTPNotFound(reason='Certificate with name {} does not exist'.format(cert_name))

    # read config
    # if cert_name is currently set for 'certificateName' in config for 'rest_api'
    cf_mgr = ConfigurationManager(connect.get_storage_async())
    result = await cf_mgr.get_category_item(category_name='rest_api', item_name='certificateName')
    if cert_name == result['value']:
        raise web.HTTPConflict(reason='Certificate with name {} is already in use, you can not delete'
                               .format(cert_name))

    msg = ''
    cert_file_found_and_removed = False
    if os.path.isfile(cert_file):
        os.remove(cert_file)
        msg = "{}.cert has been deleted successfully".format(cert_name)
        cert_file_found_and_removed = True

    key_file_found_and_removed = False
    if os.path.isfile(key_file):
        os.remove(key_file)
        msg = "{}.key has been deleted successfully".format(cert_name)
        key_file_found_and_removed = True

    if key_file_found_and_removed and cert_file_found_and_removed:
        msg = "{}.key, {}.cert have been deleted successfully".format(cert_name, cert_name)

    return web.json_response({'result': msg})


def _get_certs_dir():
    if _FOGLAMP_DATA:
        certs_dir = os.path.expanduser(_FOGLAMP_DATA + '/etc/certs')
    else:
        certs_dir = os.path.expanduser(_FOGLAMP_ROOT + '/data/etc/certs')

    return certs_dir


def _find_file(name, path):
    result = []
    for root, dirs, files in os.walk(path):
        if name in files:
            result.append(os.path.join(root, name))

    return result
