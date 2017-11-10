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

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)

_CONFIG_CATEGORY_NAME = "HTTP_TRANS"
_CONFIG_CATEGORY_DESCRIPTION = "North Plugin HTTP Translator"

# TODO: actual value for url
_DEFAULT_CONFIG = {
    "plugin": {
        "description": "http translator plugin",
        "type": "string",
        "default": "http translator"
    },
    "url": {
        "description": "URI to accept data",
        "type": "string",
        "default": "http://localhost:3000/api/reading"
    },
    "wait_to_shutdown": {
        "description": "how long (x seconds) the plugin should wait for pending tasks to complete or cancel otherwise",
        "type": "integer",
        "default": "10"
    }
}


class NorthPluginException(Exception):
    def __init__(self, reason):
        self.reason = reason


class HttpTranslatorException(NorthPluginException):
    def __init__(self, reason):
        super(HttpTranslatorException, self).__init__(reason)
        self.reason = reason


class ConfigurationError(HttpTranslatorException):
    def __init__(self, reason):
        super(ConfigurationError, self).__init__(reason)
        self.reason = reason


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
        self.config = self.initialize()
        self.tasks = []

    @classmethod
    def info(cls):
        # TODO: check type value (translator ?)
        # FIXME: plugin info should return with _DEFAULT_CONFIG or initialized config
        return {"name": "HTTP Translator", "version": 1.0, "interface": 1.0,
                "type": "translator", "config": _DEFAULT_CONFIG}

    def initialize(self):
        """ returns a JSON object:

        Used to hold instance or state information that would be needed for any future calls.
        If the initialisation fails
        then routine should raise an exception. After this exception is raised the plugin
        will not be used further.
        """
        try:
            # write (merge) config i.e. create_category
            cfg_manager = ConfigurationManager(self.storage_client)
            self.event_loop.run_until_complete(cfg_manager.create_category(_CONFIG_CATEGORY_NAME,
                                                                           _DEFAULT_CONFIG,
                                                                           _CONFIG_CATEGORY_DESCRIPTION))

            # read it and use for future stuff in this plugin
            config = self.event_loop.run_until_complete(cfg_manager.get_category_all_items(_CONFIG_CATEGORY_NAME))
            return config
        except Exception as ex:
            raise ConfigurationError(str(ex))

    def shutdown(self):
        """  Filter and cancel all pending tasks, after waiting for a threshold limit
            i.e. config["wait_to_shutdown"]

        done = sent successfully + got an error + trapped into exception
        pending =  the requests which are sent but waiting for response or in queue

        """
        self.event_loop.run_until_complete(self.cancel_tasks())

    async def cancel_tasks(self):
        # return on first exception to cancel any pending tasks
        done, pending = await asyncio.wait(self.tasks)

        # cancel any pending tasks, the tuple could be empty so it's safe
        for pending_task in pending:
            pending_task.cancel()

    async def send_payloads(self, payloads):
        """ send a list of payloads """
        async with aiohttp.ClientSession() as session:
            for p in payloads:
                task = asyncio.ensure_future(self._send(p, session))
                self.tasks.append(task)  # create list of tasks

            return await asyncio.gather(*self.tasks)  # gather task responses

    async def send_payload(self, payload):
        """ send a single payload """
        async with aiohttp.ClientSession() as session:
            resp = await self._send(payload=payload, session=session)
            return resp

    async def _send(self, payload, session):
        """Send the payload, using ClientSession."""
        url = self.config['url']['value']
        async with session.post(url, data=payload) as resp:
            resp = await resp.text()
            # TODO: if error/ exception
            return resp


if __name__ == "__main__":
    event_loop = asyncio.get_event_loop()
    storage = Storage("127.0.0.1", 34445)

    http_translator = HttpTranslatorPlugin(loop=event_loop, storage_client=storage)

    # Make an reading object payload for asset_code
    # TODO: format?
    PAYLOAD = {"asset_code": "TI Sensor Tag/temperature",
               "readings": [
                   {"read_key": "f1cfff7a-3769-4f47-9ded-00f0975d66f5",
                    "reading": {"temperature": 41, "humidity": 88},
                    "user_ts": "2017-10-11 15:10:51.927191906"
                    },
                   {"read_key": "78f73c9f-bc11-4b8d-a246-58863adf66b5",
                    "reading": {"temperature": 41, "humidity": 88},
                    "user_ts": "2017-10-11 15:10:51.930077316"
                    }]
               }

    PAYLOAD_2 = {"asset_code": "TI Sensor Tag/temperature",
                 "reading": {"read_key": "f1cfff7a-3769-4f47-9ded-00f0975d66f5",
                             "reading": {"temperature": 41, "humidity": 88},
                             "user_ts": "2017-10-11 15:10:51.927191906"
                             }
                 }
    result = event_loop.run_until_complete(http_translator.send_payload(PAYLOAD_2))
    print("Single", result)

    result = event_loop.run_until_complete(http_translator.send_payloads([PAYLOAD, PAYLOAD_2]))
    print("Multiple", result)
