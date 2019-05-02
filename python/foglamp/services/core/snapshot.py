# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Provides utility functions to take snapshot of plugins"""

import os
from os import path
from os.path import basename
import json
import tarfile
import fnmatch
import time
from collections import OrderedDict

from foglamp.common import logger
from foglamp.common.common import _FOGLAMP_ROOT


__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2019 Dianomic Systems"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)
_NO_OF_FILES_TO_RETAIN = 3
SNAPSHOT_PREFIX = "snapshot-plugin"


class SnapshotPluginBuilder:

    _out_file_path = None
    _interim_file_path = None

    def __init__(self, snapshot_plugin_dir):
        try:
            if not os.path.exists(snapshot_plugin_dir):
                os.makedirs(snapshot_plugin_dir)
            else:
                self.check_and_delete_plugins_tar_files(snapshot_plugin_dir)

            self._out_file_path = snapshot_plugin_dir
            self._interim_file_path = snapshot_plugin_dir
        except (OSError, Exception) as ex:
            _LOGGER.error("Error in initializing SnapshotPluginBuilder class: %s ", str(ex))
            raise RuntimeError(str(ex))

    async def build(self):
        def reset(tarinfo):
            tarinfo.uid = tarinfo.gid = 0
            tarinfo.uname = tarinfo.gname = "root"
            return tarinfo

        tar_file_name = ""
        try:
            snapshot_id = str(int(time.time()))
            snapshot_filename = "{}-{}.tar.gz".format(SNAPSHOT_PREFIX, snapshot_id)
            tar_file_name = "{}/{}".format(self._out_file_path, snapshot_filename)
            pyz = tarfile.open(tar_file_name, "w:gz")
            try:
                # files are being added to tarfile with relative path and NOT with absolute path.
                pyz.add("{}/python/foglamp/plugins".format(_FOGLAMP_ROOT),
                        arcname="python/foglamp/plugins", recursive=True)
                # C plugins location is different with "make install" and "make"
                if path.exists("{}/bin".format(_FOGLAMP_ROOT)) and path.exists("{}/bin/foglamp".format(_FOGLAMP_ROOT)):
                    pyz.add("{}/plugins".format(_FOGLAMP_ROOT), arcname="plugins", recursive=True, filter=reset)
                else:
                    pyz.add("{}/C/plugins".format(_FOGLAMP_ROOT), arcname="C/plugins", recursive=True)
                    pyz.add("{}/plugins".format(_FOGLAMP_ROOT), arcname="plugins", recursive=True)
                    pyz.add("{}/cmake_build/C/plugins".format(_FOGLAMP_ROOT), arcname="cmake_build/C/plugins",
                            recursive=True)
            finally:
                pyz.close()
        except Exception as ex:
            if os.path.isfile(tar_file_name):
                os.remove(tar_file_name)
            _LOGGER.error("Error in creating Snapshot .tar.gz file: %s ", str(ex))
            raise RuntimeError(str(ex))

        self.check_and_delete_temp_files(self._interim_file_path)
        self.check_and_delete_plugins_tar_files(self._out_file_path)
        _LOGGER.info("Snapshot %s successfully created.", tar_file_name)
        return snapshot_id, snapshot_filename

    def check_and_delete_plugins_tar_files(self, snapshot_plugin_dir):
        valid_extension = '.tar.gz'
        valid_files_to_delete = dict()
        try:
            for root, dirs, files in os.walk(snapshot_plugin_dir):
                for _file in files:
                    if _file.endswith(valid_extension):
                        valid_files_to_delete[_file.split(".")[0]] = os.path.join(root, _file)
            valid_files_to_delete_sorted = OrderedDict(sorted(valid_files_to_delete.items(), reverse=True))
            while len(valid_files_to_delete_sorted) > _NO_OF_FILES_TO_RETAIN:
                _file, _path = valid_files_to_delete_sorted.popitem()
                _LOGGER.warning("Removing plugin snapshot file %s.", _path)
                os.remove(_path)
        except OSError as ex:
            _LOGGER.error("ERROR while deleting plugin file", str(ex))

    def check_and_delete_temp_files(self, snapshot_plugin_dir):
        # Delete all non *.tar.gz files
        for f in os.listdir(snapshot_plugin_dir):
            if not fnmatch.fnmatch(f, '{}*.tar.gz'.format(SNAPSHOT_PREFIX)):
                os.remove(os.path.join(snapshot_plugin_dir, f))

    def write_to_tar(self, pyz, temp_file, data):
        with open(temp_file, 'w') as outfile:
            json.dump(data, outfile, indent=4)
        pyz.add(temp_file, arcname=basename(temp_file))

    def extract_files(self, pyz):
        # Extraction methods are different for production env and dev env
        if path.exists("{}/bin".format(_FOGLAMP_ROOT)) and path.exists("{}/bin/foglamp".format(_FOGLAMP_ROOT)):
            cmd = "{}/extras/C/cmdutil tar-extract {}".format(_FOGLAMP_ROOT, pyz)
            retcode = os.system(cmd)
            if retcode != 0:
                raise OSError('Error {}: {}'.format(retcode, cmd))
            return True
        else:
            try:
                with tarfile.open(pyz, "r:gz") as tar:
                    # Since we are storing full path of the files, we need to specify "/" as the path to restore
                    tar.extractall(path=_FOGLAMP_ROOT, members=tar.getmembers())
            except Exception as ex:
                raise RuntimeError("Extraction error for snapshot {}. {}".format(pyz, str(ex)))
            else:
                return True
