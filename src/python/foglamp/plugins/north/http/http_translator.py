# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" HTTP Translator """

import aiohttp
import asyncio

from foglamp import logger
from foglamp.configuration_manager import ConfigurationManager
from foglamp.storage.storage import Storage
from foglamp.plugins.north.http.exceptions import *

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)


http_translator = None

# Configuration related to HTTP Translator
_CONFIG_CATEGORY_NAME = "HTTP_TRANS"
_CONFIG_CATEGORY_DESCRIPTION = "North Plugin HTTP Translator"

_DEFAULT_CONFIG = {
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
# As per specs it should be plugin_info
# def plugin_info():

def plugin_retrieve_info():
    return {
        'name': 'http_translator',
        'version': '1.0.0',
        'type': 'translator',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(loop, storage_client):
    global http_translator  # FIX ME: don't use global
    # loop = asyncio.get_event_loop()
    http_translator = HttpTranslatorPlugin(loop, storage_client)
    http_translator.initialize()
    return http_translator.config


def plugin_send(cfg, payload):
    return http_translator.send_payload(cfg, payload)


def plugin_shutdown():
    http_translator.shutdown()


# TODO: (ASK) North plugin can not be reconfigured? (per callback mechanism)
def plugin_reconfigure():
    pass


class HttpTranslatorPlugin(object):
    """ North HTTP Translator Plugin """

    def __init__(self, loop, storage_client):
        """
        Args:

        loop: asyncio event loop
        storage_client: storage object
        """
        self.event_loop = asyncio.get_event_loop() if loop is None else loop
        self.storage_client = storage_client
        self.config = dict()
        self.tasks = []

    def initialize(self):
        """ returns a JSON object:

        Used to hold instance or state information that would be needed for any future calls.
        If the initialisation fails
        then routine should raise an exception. After this exception is raised the plugin
        will not be used further.
        """
        try:
            # TODO: (ASK) which code will do this? sending task Or this plugin

            # write (merge) config i.e. create_category
            cfg_manager = ConfigurationManager(self.storage_client)
            self.event_loop.run_until_complete(cfg_manager.create_category(_CONFIG_CATEGORY_NAME,
                                                                           _DEFAULT_CONFIG,
                                                                           _CONFIG_CATEGORY_DESCRIPTION))

            # read it and use for future stuff in this plugin
            self.config = self.event_loop.run_until_complete(cfg_manager.get_category_all_items(_CONFIG_CATEGORY_NAME))
        except Exception as ex:
            _LOGGER.exception("Can not initialize the plugin, Got configuration error %s", str(ex))
            raise ConfigurationError(str(ex))
            # TODO: should sys.exit(1) ?

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
            wait_for = self.config['shutdown_wait_time']['value']
            pass

        # cancel any pending tasks, the tuple could be empty so it's safe
        for pending_task in pending:
            pending_task.cancel()

    def send_payloads(self, cfg, payloads):
        self.config = cfg
        res = self.event_loop.run_until_complete(self._send_payloads(payloads))
        return res

    # TODO: check needed?
    # in case you want to send list of blocks for diff asset codes
    async def _send_payloads(self, payloads):
        """ send a list of block payloads """
        async with aiohttp.ClientSession() as session:
            for p in payloads:
                task = asyncio.ensure_future(self._send(p, session))
                self.tasks.append(task)  # create list of tasks

            return await asyncio.gather(*self.tasks)  # gather task responses

    def send_payload(self, cfg, payload):
        self.config = cfg
        # TODO: validate payload? as per specified format;
        # perhaps not needed, as sending process is reading from the readings table
        # and error handling, logging is being handled by _send def, and it returns actual response
        resp = self.event_loop.run_until_complete(self._send_payload(payload))
        return resp

    async def _send_payload(self, payload):
        """ Send a single block payload """
        async with aiohttp.ClientSession() as session:
            resp = await self._send(payload=payload, session=session)
            return resp

    async def _send(self, payload, session):
        """ Send the payload, using ClientSession """
        url = self.config['url']['value']
        headers = {'content-type': 'application/json'}
        async with session.post(url, data=payload, headers=headers) as resp:
            result = await resp.text()
            status_code = resp.status
            if status_code in range(400, 500):
                _LOGGER.error("Bad request error code: %d, reason: %s", status_code, resp.reason)
            if status_code in range(500, 600):
                _LOGGER.error("Server error code: %d, reason: %s", status_code, resp.reason)

            return result


if __name__ == "__main__":
    import json
    event_loop = asyncio.get_event_loop()
    storage = Storage("127.0.0.1", 38717)

    print(plugin_retrieve_info())
    # print(plugin_info()) # should be this

    config = plugin_init(event_loop, storage)
    print(config)

    reading_block_payload = {
        'asset_code': 'TI Sensor Tag/temperature',
        'readings': [
            {
                'read_key': 'f1cfff7a-3769-4f47-9ded-00f0975d66f5',
                'reading': {
                    'temperature': 41,
                    'humidity': 88
                },
                'timestamp': '2017-10-11 15:10:51.927191906'
            }
        ]
    }
    result = plugin_send(config, json.dumps(reading_block_payload))
    print(result)

    # to test this, make sure plugin_send def calls http_translator.send_payloads
    # reading_block_payloads = [json.dumps(reading_block_payload),
    # json.dumps(reading_block_payload), json.dumps(reading_block_payload)]

    # m_result = plugin_send(config, reading_block_payloads)
    # print(m_result)

    plugin_shutdown()
