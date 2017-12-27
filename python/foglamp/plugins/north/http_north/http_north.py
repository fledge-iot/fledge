# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" HTTP North """

import aiohttp
import asyncio
import json

from foglamp.common import logger
from foglamp.plugins.north.common.common import *

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)


http_north = None
config = ""

# Configuration related to HTTP North
_CONFIG_CATEGORY_NAME = "HTTP_TR"
_CONFIG_CATEGORY_DESCRIPTION = "HTTP North Plugin"

_DEFAULT_CONFIG = {
    'plugin': {
         'description': 'HTTP North Plugin',
         'type': 'string',
         'default': 'http_north'
    },
    'url': {
        'description': 'URI to accept data',
        'type': 'string',
        'default': 'http://localhost:8118/ingress/messages'
    },
    'shutdown_wait_time': {
        'description': 'how long (x seconds) the plugin should wait for pending tasks to complete or cancel otherwise',
        'type': 'integer',
        'default': '10'
    }
}


# TODO write to Audit Log
def plugin_info():
    return {
        'name': 'http_north',
        'version': '1.0.0',
        'type': 'north',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(data):
    global http_north, config
    http_north = HttpNorthPlugin()
    config = data
    return config


def plugin_send(data, payload, stream_id):
    return http_north.send_payloads(payload, stream_id)


def plugin_shutdown(data):
    http_north.shutdown()


# TODO: (ASK) North plugin can not be reconfigured? (per callback mechanism)
def plugin_reconfigure():
    pass


class HttpNorthPlugin(object):
    """ North HTTP Plugin """

    def __init__(self):
        self.event_loop = asyncio.get_event_loop()
        self.tasks = []

    def shutdown(self):
        """  Filter and cancel all pending tasks,

        After waiting for a threshold limit i.e. config["wait_to_shutdown"]

        done = sent successfully + got an error + trapped into exception
        pending =  the requests (tasks) waiting for response Or in queue

        """
        self.event_loop.run_until_complete(self.cancel_tasks())

    async def cancel_tasks(self):
        # cancel pending tasks

        if len(self.tasks) == 0:
            return

        done, pending = await asyncio.wait(self.tasks)

        if len(pending):
            # FIXME: (ASK) wait for some fixed time? or Configurable
            wait_for = config['shutdown_wait_time']['value']
            pass

        # cancel any pending tasks, the tuple could be empty so it's safe
        for pending_task in pending:
            pending_task.cancel()

    def send_payloads(self, payloads, stream_id):
        is_data_sent = False
        new_last_object_id = 0
        num_sent = 0
        try:
            new_last_object_id, num_sent = self.event_loop.run_until_complete(self._send_payloads(payloads))
            is_data_sent = True
        except Exception as ex:
            _LOGGER.exception("Data could not be sent, %s", str(ex))

        return is_data_sent, new_last_object_id, num_sent

    async def _send_payloads(self, payloads):
        """ send a list of block payloads """
        num_count = 0
        last_id = None
        async with aiohttp.ClientSession() as session:
            payload_to_be_send = list()
            for payload in payloads:
                num_count += 1
                last_id = payload['id']
                p = {"asset_code": payload['asset_code'],
                     "readings": [{
                         "read_key": payload['read_key'],
                         "user_ts": payload['user_ts'],
                         "reading": payload['reading']
                     }]}
                payload_to_be_send.append(p)
            task = asyncio.ensure_future(self._send(payload_to_be_send, session))
            self.tasks.append(task)  # create list of tasks
            await asyncio.gather(*self.tasks)  # gather task responses
        return last_id, num_count

    async def _send(self, payload, session):
        """ Send the payload, using ClientSession """
        url = config['url']['value']
        headers = {'content-type': 'application/json'}
        async with session.post(url, data=json.dumps(payload), headers=headers) as resp:
            result = await resp.text()
            status_code = resp.status
            if status_code in range(400, 500):
                _LOGGER.error("Bad request error code: %d, reason: %s", status_code, resp.reason)
            if status_code in range(500, 600):
                _LOGGER.error("Server error code: %d, reason: %s", status_code, resp.reason)

            return result
