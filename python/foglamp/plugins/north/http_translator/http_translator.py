# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

""" HTTP Translator """
import json

import requests
import time

import foglamp.plugins.north.common.common as plugin_common
import foglamp.plugins.north.common.exceptions as plugin_exceptions
from foglamp.common import logger

__author__ = "Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = None
_DEFAULT_CONFIG = {
    'plugin': {
         'description': 'Python module name of the plugin to load',
         'type': 'string',
         'default': 'http_translator'
    },
    'URL': {
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
        'name': 'http_translator',
        'version': '1.0.0',
        'type': 'translator',
        'interface': '1.0',
        'config': _DEFAULT_CONFIG
    }


def plugin_init(data):
    # TODO: compare instance fetching via inspect vs as param passing
    # import inspect
    # sending_process_instance = inspect.currentframe().f_back.f_locals['self']
    return {'URL': data['URL']['value'], 'sending_process_instance': data['sending_process_instance']}

def plugin_send(data, payload, stream_id):
    global _logger
    url = data['URL']
    sending_process_instance = data['sending_process_instance']
    _logger = logger.setup(__name__ + "_" + str(stream_id))
    _logger.debug("{0} - ".format("plugin_init"))
    return HttpTranslatorPlugin(sending_process_instance).translate_and_send_payload(url, payload, stream_id)

def plugin_shutdown(data):
    pass

def plugin_reconfigure():
    pass


class HttpTranslatorPlugin(object):
    """ North HTTP Translator Plugin """

    def __init__(self, sending_process_instance):
        self._sending_process_instance = sending_process_instance

    def translate_and_send_payload(self, url, payload, stream_id):
        is_data_sent = False
        new_last_object_id = 0
        num_sent = 0
        translated_payload = list()
        try:
            new_last_object_id, num_sent, translated_payload = self._translate(payload, stream_id)
            is_data_sent = self._send_to_url(url, {"Content-Type": 'application/json'}, translated_payload)
        except Exception as ex:
            _logger.exception("Data could not be sent, %s", str(ex))
        else:
            _logger.info("HTTP translation done. Data sent, %s, %d", new_last_object_id, num_sent)
        return is_data_sent, new_last_object_id, num_sent

    def _translate(self, payload, stream_id):
        num_count = 0
        last_id = None
        translated_payload = list()
        for p in payload:
            num_count += 1
            last_id = p['id']
            q = {"asset_code": p['asset_code'],
                 "readings": [{
                     "read_key": p['read_key'],
                     "user_ts": p['user_ts'],
                     "reading": p['reading']
                 }]}
            translated_payload.append(q)
        return last_id, num_count, translated_payload

    # TODO: Move this method to parent sending process and access here via self._sending_process_instance
    def _send_to_url(self, url, header, data, max_retry=3, timeout=10):
        sleep_time = 0.5
        message_type = 'Data'
        _message = ""
        _error = False
        num_retry = 1
        msg_header = header
        data_json = json.dumps(data)
        _logger.debug("message : |{0}| |{1}| ".format(message_type, data_json))

        while num_retry < max_retry:
            _error = False
            try:
                response = requests.post(url,
                                         headers=msg_header,
                                         data=data_json,
                                         verify=False,
                                         timeout=timeout)
            except Exception as e:
                _message = plugin_common.MESSAGES_LIST["e000024"].format(e)
                _error = Exception(_message)
            else:
                # Evaluate the HTTP status codes
                if not str(response.status_code).startswith('2'):
                    tmp_text = str(response.status_code) + " " + response.text
                    _message = plugin_common.MESSAGES_LIST["e000024"].format(tmp_text)
                    _error = plugin_exceptions.URLFetchError(_message)
                    _logger.debug("message type |{0}| response: |{1}| |{2}| ".format(message_type,
                                                                                 response.status_code,
                                                                                 response.text))
            if _error:
                time.sleep(sleep_time)
                num_retry += 1
                sleep_time *= 2
            else:
                break

        if _error:
            _logger.warning(_message)
            raise

        return False if _error else True

