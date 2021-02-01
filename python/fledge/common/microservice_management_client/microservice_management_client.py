# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

import http.client
import json
import urllib.parse
from fledge.common import logger
from fledge.common.microservice_management_client import exceptions as client_exceptions

__author__ = "Ashwin Gopalakrishnan"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_logger = logger.setup(__name__)


class MicroserviceManagementClient(object):
    _management_client_conn = None

    def __init__(self, microservice_management_host, microservice_management_port):
        self._management_client_conn = http.client.HTTPConnection("{0}:{1}".format(microservice_management_host, microservice_management_port))

    def register_service(self, service_registration_payload):
        """ Registers a newly created microservice with the core service

        The core service will persist this information in memory rather than write it to the storage layer since it will
        change on every run of Fledge.


        :param service_registration_payload: A dict object describing the microservice and giving details of the
        management interface for that microservice
        :return: a JSON object containing the UUID of the newly registered service
        """
        url = '/fledge/service'

        self._management_client_conn.request(method='POST', url=url, body=json.dumps(service_registration_payload))
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        if r.status in range(500, 600):
            _logger.error("Server error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        try:
            response["id"]
        except (KeyError, Exception) as ex:
            _logger.exception("Could not register the microservice, From request %s, Reason: %s", json.dumps(service_registration_payload), str(ex))
            raise

        return response

    def unregister_service(self, microservice_id):
        """ Removes the registration record for a microservice

        This is usually called by the microservice itself as part of its shutdown procedure, although this may not be
        the only time it is called. A service may unregister, do some maintenance type operation and then re-register
        if it desires.

        :param microservice_id: string UUID of microservice
        :return: a JSON object containing the UUID of the unregistered service
        """
        url = '/fledge/service/{}'.format(microservice_id)

        self._management_client_conn.request(method='DELETE', url=url)
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        if r.status in range(500, 600):
            _logger.error("Server error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        try:
            response["id"]
        except (KeyError, Exception) as ex:
            _logger.exception("Could not unregister the micro-service having uuid %s, Reason: %s",
                              microservice_id, str(ex))
            raise

        return response

    def register_interest(self, category, microservice_id):
        """ Register an interest of microservice in a configuration category

        :param category: configuration category
        :param microservice_id: microservice's UUID string
        :return: A JSON object containing a registration ID for this registration
        """

        url = '/fledge/interest'

        payload = json.dumps({"category": category, "service": microservice_id}, sort_keys=True)
        self._management_client_conn.request(method='POST', url=url, body=payload)
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        if r.status in range(500, 600):
            _logger.error("Server error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        try:
            response["id"]
        except (KeyError, Exception) as ex:
            _logger.exception("Could not register interest, for request payload %s, Reason: %s",
                              payload, str(ex))
            raise

        return response

    def unregister_interest(self, registered_interest_id):
        """ Remove a previously registered interest in a configuration category

        :param registered_interest_id: registered interest id for a configuration category
        :return: A JSON object containing the unregistered interest id
        """
        url = '/fledge/interest/{}'.format(registered_interest_id)

        self._management_client_conn.request(method='DELETE', url=url)
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        if r.status in range(500, 600):
            _logger.error("Server error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        try:
            response["id"]
        except (KeyError, Exception) as ex:
            _logger.exception("Could not unregister interest for %s, Reason: %s", registered_interest_id, str(ex))
            raise

        return response

    def get_services(self, service_name=None, service_type=None):
        """ Retrieve the details of one or more services that are registered

        :param service_name: filter the returned services by name
        :param service_type: filter the returned services by type
        :return: list of registered microservices, all or based on filter(s) applied
        """
        url = '/fledge/service'
        delimeter = '?'
        if service_name:
            url = '{}{}name={}'.format(url, delimeter, urllib.parse.quote(service_name))
            delimeter = '&'
        if service_type:
            url = '{}{}type={}'.format(url, delimeter, service_type)

        self._management_client_conn.request(method='GET', url=url)
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        if r.status in range(500, 600):
            _logger.error("Server error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        try:
            response["services"]
        except (KeyError, Exception) as ex:
            _logger.exception("Could not find the micro-service for requested url %s, Reason: %s", url, str(ex))
            raise

        return response

    def get_configuration_category(self, category_name=None):
        """

        :param category_name:
        :return:
        """
        url = '/fledge/service/category'

        if category_name:
            url = "{}/{}".format(url, urllib.parse.quote(category_name))

        self._management_client_conn.request(method='GET', url=url)
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        if r.status in range(500, 600):
            _logger.error("Server error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        return response

    def get_configuration_item(self, category_name, config_item):
        """

        :param category_name:
        :param config_item:
        :return:
        """
        url = "/fledge/service/category/{}/{}".format(urllib.parse.quote(category_name), urllib.parse.quote(config_item))

        self._management_client_conn.request(method='GET', url=url)
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        if r.status in range(500, 600):
            _logger.error("Server error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        return response

    def create_configuration_category(self, category_data):
        """

        :param category_data: e.g. '{"key": "TEST", "description": "description", "value": {"info": {"description": "Test", "type": "boolean", "default": "true"}}}'
        :return:
        """
        data = json.loads(category_data)
        if 'keep_original_items' in data:
            keep_original_item = 'true' if data['keep_original_items'] is True else 'false'
            url = '/fledge/service/category?keep_original_items={}'.format(keep_original_item)
            del data['keep_original_items']
        else:
            url = '/fledge/service/category'

        self._management_client_conn.request(method='POST', url=url, body=json.dumps(data))
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        if r.status in range(500, 600):
            _logger.error("Server error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        return response

    def create_child_category(self, parent, children):
        """
        :param parent string
        :param children list
        :return:
        """
        data = {"children": children}
        url = '/fledge/service/category/{}/children'.format(urllib.parse.quote(parent))

        self._management_client_conn.request(method='POST', url=url, body=json.dumps(data))
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        if r.status in range(500, 600):
            _logger.error("Server error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        return response

    def update_configuration_item(self, category_name, config_item, category_data):
        """

        :param category_name:
        :param config_item:
        :param category_data: e.g. '{"value": "true"}'
        :return:
        """
        url = "/fledge/service/category/{}/{}".format(urllib.parse.quote(category_name), urllib.parse.quote(config_item))

        self._management_client_conn.request(method='PUT', url=url, body=category_data)
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        if r.status in range(500, 600):
            _logger.error("Server error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        return response

    def delete_configuration_item(self, category_name, config_item):
        """

        :param category_name:
        :param config_item:
        :return:
        """
        url = "/fledge/service/category/{}/{}/value".format(urllib.parse.quote(category_name), urllib.parse.quote(config_item))

        self._management_client_conn.request(method='DELETE', url=url)
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        if r.status in range(500, 600):
            _logger.error("Server error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        return response

    def get_asset_tracker_events(self):
        url = '/fledge/track'
        self._management_client_conn.request(method='GET', url=url)
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        if r.status in range(500, 600):
            _logger.error("Server error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        return response

    def create_asset_tracker_event(self, asset_event):
        """

        :param asset_event
               e.g. {"asset": "AirIntake", "event": "Ingest", "service": "PT100_In1", "plugin": "PT100"}
        :return:
        """
        url = '/fledge/track'
        self._management_client_conn.request(method='POST', url=url, body=json.dumps(asset_event))
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        if r.status in range(500, 600):
            _logger.error("Server error code: %d, Reason: %s", r.status, r.reason)
            raise client_exceptions.MicroserviceManagementClientError(status=r.status, reason=r.reason)
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        return response
