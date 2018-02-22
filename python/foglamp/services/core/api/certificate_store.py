# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import os
from aiohttp import web
from foglamp.common import logger

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


_FOGLAMP_DATA = os.getenv("FOGLAMP_DATA", default=None)
_FOGLAMP_ROOT = os.getenv("FOGLAMP_ROOT", default='/usr/local/foglamp')


_logger = logger.setup(__name__, level=20)

_help = """
    -------------------------------------------------------------------------------
    | POST             | /foglamp/certificate                                          |
    -------------------------------------------------------------------------------
"""

async def upload(request):
    """

    :Example:
        curl -F "key=@filename.key" -F "cert=@filename.cert" http://localhost:8081/foglamp/certificate

    """
    data = await request.post()

    # contains the name of the file in string format
    key_file = data.get('key')
    cert_file = data.get('cert')

    # TODO: handle overwrite if file with the same name already exists?
    allow_overwrite = data.get('overwrite', 0)
    should_overwrite = True if allow_overwrite == 1 else False

    if not key_file or not cert_file:
        raise web.HTTPBadRequest(reason="key or certs file is missing")

    key_filename = key_file.filename
    cert_filename = cert_file.filename

    # accepted extensions are '.key and .cert'
    valid_extensions = ('.key', '.cert')
    if not cert_filename.endswith(valid_extensions) or not key_filename.endswith(valid_extensions):
        raise web.HTTPBadRequest(reason="Accepted file extensions are .key and .cert")

    # certs and key filenames should match
    if cert_filename and key_filename:
        if cert_filename.split(".")[0] != key_filename.split(".")[0]:
            raise web.HTTPBadRequest(reason="key and certs file name should match")

    if _FOGLAMP_DATA:
        certs_dir = os.path.expanduser(_FOGLAMP_DATA + '/etc/certs')
    else:
        certs_dir = os.path.expanduser(_FOGLAMP_ROOT + '/data/etc/certs')

    # TODO: if should_overwrite
    # check certs dir has file with the same name?
    # if yes then only overwrite if should_overwrite

    # .file contains the actual file data that needs to be stored somewhere
    # write file contents to cert path on the basis of os env variable
    if key_file:
        key_file_data = data['key'].file
        key_file_content = key_file_data.read()
        key_file_path = certs_dir + '/{}'.format(key_filename)
        with open(key_file_path, 'wb') as f:
            f.write(key_file_content)

    if cert_file:
        cert_file_data = data['cert'].file
        cert_file_content = cert_file_data.read()
        cert_file_path = certs_dir + '/{}'.format(cert_filename)
        with open(cert_file_path, 'wb') as f:
            f.write(cert_file_content)

    # in order to bring this new cert usage into effect, make sure to
    # update config for category rest_api
    # and reboot
    return web.json_response({"result": "{} and {} have been uploaded successfully"
                             .format(key_filename, cert_filename)})
