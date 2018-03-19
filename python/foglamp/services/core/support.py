# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" Provides utility functions to build a FogLAMP Support bundle.
"""

import datetime
import os
from os.path import basename
import glob
import sys
import shutil
import json
import tarfile
import asyncio
import fnmatch
import aiohttp
import subprocess
from foglamp.services.core.connect import *
from foglamp.common import logger

__author__ = "Amarendra K Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__, level=20)
_NO_OF_FILES_TO_RETAIN = 3
_SYSLOG_FILE = '/var/log/syslog'


class SupportBuilder:

    _out_file_path = None
    _interim_file_path = None
    _base_url = None
    _headers = None
    _storage = None
    _rest_api_port = None
    
    def __init__(self, support_dir, base_url):
        try:
            if not os.path.exists(support_dir):
                os.makedirs(support_dir)
            else:
                self.check_and_delete_bundles(support_dir)

            self._out_file_path = support_dir
            self._interim_file_path = support_dir
            self._base_url = base_url
            self._headers = {"Content-Type": 'application/json'}
            self._storage = get_storage()  # from foglamp.services.core.connect
        except (OSError, Exception) as ex:
            _LOGGER.error("Error in initializing SupportBuilder class: %s ", str(ex))
            raise RuntimeError(str(ex))

    async def build(self):
        try:
            loop = asyncio.get_event_loop()
            today = datetime.datetime.now()
            file_spec = today.strftime('%y%m%d-%H-%M-%S')
            tar_file_name = self._out_file_path+"/"+"support-{}.tar.gz".format(file_spec)
            pyz = tarfile.open(tar_file_name, "w:gz")
            try:
                self.add_syslog_foglamp(pyz, file_spec)
                self.add_syslog_storage(pyz, file_spec)
                self.add_table_configuration(pyz, file_spec)
                self.add_table_audit_log(pyz, file_spec)
                self.add_table_schedules(pyz, file_spec)
                self.add_table_scheduled_processes(pyz, file_spec)
                await self.add_service_registry(pyz, file_spec, loop=loop)
                self.add_machine_resources(pyz, file_spec)
                self.add_psinfo(pyz, file_spec)
            finally:
                pyz.close()
        except Exception as ex:
            _LOGGER.error("Error in creating Support .tar.gz file: %s ", str(ex))
            raise RuntimeError(str(ex))

        self.check_and_delete_temp_files(self._interim_file_path)
        _LOGGER.info("Support bundle %s successfully created.", tar_file_name)
        return tar_file_name

    def check_and_delete_bundles(self, support_dir):
        files = glob.glob(support_dir + "/" + "support*.tar.gz")
        files.sort(key=os.path.getmtime)
        if len(files) >= _NO_OF_FILES_TO_RETAIN:
            for f in files[:-2]:
                if os.path.isfile(f):
                    os.remove(os.path.join(support_dir, f))

    def check_and_delete_temp_files(self, support_dir):
        # Delete all non *.tar.gz files
        for f in os.listdir(support_dir):
            if not fnmatch.fnmatch(f, 'support*.tar.gz'):
                os.remove(os.path.join(support_dir, f))

    def write_to_tar(self, pyz, temp_file, data):
        with open(temp_file, 'w') as outfile:
            json.dump(data, outfile, indent=4)
        pyz.add(temp_file, arcname=basename(temp_file))

    def add_syslog_foglamp(self, pyz, file_spec):
        # The foglamp entries from the syslog file
        temp_file = self._interim_file_path + "/" + "syslog-{}".format(file_spec)
        try:
            subprocess.call("grep -n '{}' {} > {}".format("FogLAMP", _SYSLOG_FILE, temp_file), shell=True)
        except OSError as ex:
            raise RuntimeError("Error in creating {}. Error-{}".format(temp_file, str(ex)))
        pyz.add(temp_file, arcname=basename(temp_file))

    def add_syslog_storage(self, pyz, file_spec):
        # The contents of the syslog file that relate to the database layer (postgres)
        temp_file = self._interim_file_path + "/" + "syslogStorage-{}".format(file_spec)
        try:
            subprocess.call("grep -n '{}' {} > {}".format("FogLAMP Storage", _SYSLOG_FILE, temp_file), shell=True)
        except OSError as ex:
            raise RuntimeError("Error in creating {}. Error-{}".format(temp_file, str(ex)))
        pyz.add(temp_file, arcname=basename(temp_file))

    def add_table_configuration(self, pyz, file_spec):
        # The contents of the configuration table from the storage layer
        temp_file = self._interim_file_path + "/" + "configuration-{}".format(file_spec)
        data = self._storage.query_tbl("configuration")
        self.write_to_tar(pyz, temp_file, data)

    def add_table_audit_log(self, pyz, file_spec):
        # The contents of the audit log from the storage layer
        temp_file = self._interim_file_path + "/" + "audit-{}".format(file_spec)
        data = self._storage.query_tbl("log")
        self.write_to_tar(pyz, temp_file, data)

    def add_table_schedules(self, pyz, file_spec):
        # The contents of the schedules table from the storage layer
        temp_file = self._interim_file_path + "/" + "schedules-{}".format(file_spec)
        data = self._storage.query_tbl("schedules")
        self.write_to_tar(pyz, temp_file, data)

    def add_table_scheduled_processes(self, pyz, file_spec):
        temp_file = self._interim_file_path + "/" + "scheduled_processes-{}".format(file_spec)
        data = self._storage.query_tbl("scheduled_processes")
        self.write_to_tar(pyz, temp_file, data)

    async def add_service_registry(self, pyz, file_spec, loop=None):
        # The contents of the service registry
        temp_file = self._interim_file_path + "/" + "service_registry-{}".format(file_spec)
        loop = asyncio.get_event_loop() if loop is None else loop
        url_ping = self._base_url+'/service'
        connector = aiohttp.TCPConnector(verify_ssl=False)
        async with aiohttp.ClientSession(loop=loop, connector=connector) as session:
            async with session.get(url_ping) as resp:
                r = await resp.json()
                data = {
                    "about": "Service Registry",
                    "serviceRegistry": r
                }
        self.write_to_tar(pyz, temp_file, data)

    def add_machine_resources(self, pyz, file_spec):
        # Details of machine resources, memory size, amount of available memory, storage size and amount of free storage
        temp_file = self._interim_file_path + "/" + "machine-{}".format(file_spec)
        total, used, free = shutil.disk_usage("/")
        memory = subprocess.Popen('free -h', shell=True, stdout=subprocess.PIPE).stdout.readlines()[1].split()[1:]
        data = {
            "about": "Machine resources",
            "platform": sys.platform,
            "totalMemory": memory[0].decode(),
            "usedMemory": memory[1].decode(),
            "freeMemory": memory[2].decode(),
            "totalDiskSpace_MB": int(total / (1024 * 1024)),
            "usedDiskSpace_MB": int(used / (1024 * 1024)),
            "freeDiskSpace_MB": int(free / (1024 * 1024)),
        }
        self.write_to_tar(pyz, temp_file, data)

    def add_psinfo(self, pyz, file_spec):
        # A PS listing of al the python applications running on the machine
        temp_file = self._interim_file_path + "/" + "psinfo-{}".format(file_spec)
        a = subprocess.Popen(
            'ps -eaf | grep python3', shell=True, stdout=subprocess.PIPE).stdout.readlines()[:-2]  # remove ps command
        c = [b.decode() for b in a]  # Since "a" contains return value in bytes, convert it to string
        data = {
            "runningPythonProcesses": c
        }
        self.write_to_tar(pyz, temp_file, data)
