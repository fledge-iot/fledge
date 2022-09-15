# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import logging
import json
import asyncio
import re

from aiohttp import web
from fledge.common import logger
from fledge.services.core import connect
from fledge.common.audit_logger import AuditLogger
from fledge.services.core import connect

__author__ = "Deepanshu Yadav"
__copyright__ = "Copyright (c) 2022, Dianomic Systems Inc."
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_help = """
    ----------------------------------------------------------
    | GET            | /fledge/update               |
    ----------------------------------------------------------
"""

_LOGGER = logger.setup(__name__, level=logging.INFO)


async def get_updates(request: web.Request) -> web.Response:
    update_cmd = "sudo apt update"
    update_process = await asyncio.create_subprocess_shell(update_cmd,
                                                           stdout=asyncio.subprocess.PIPE,
                                                           stderr=asyncio.subprocess.PIPE)

    _, _ = await update_process.communicate()
    if update_process.returncode != 0:
        _LOGGER.error("Could not run {}".format(update_cmd))
        return web.json_response({'updates': []})

    cmd = "apt list --upgradable | grep \^fledge"
    installed_packages_process = await asyncio.create_subprocess_shell(cmd,
                                                                 stdout=asyncio.subprocess.PIPE,
                                                                 stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await installed_packages_process.communicate()
    if installed_packages_process.returncode == 0:
        process_output = stdout.decode("utf-8")
        _LOGGER.info(process_output)
        # split on new-line
        word_list = re.split(r"\n+", process_output)

        # remove '' from the list
        word_list = [w for w in word_list if w != '']
        packages = []

        # Now match the character / . The string before / is the actual package name we want.
        for word in word_list:
            word_match = re.findall(r".*[/]", word)
            if len(word_match) > 0:
                packages.append(word_match[0].replace('/', ''))

        # Make a set to avoid duplicates.
        upgradable_packages = list(set(packages))
        return web.json_response({'updates': upgradable_packages})
    else:
        _LOGGER.info("Updates are not available at the moment.")
        return web.json_response({'updates': []})
