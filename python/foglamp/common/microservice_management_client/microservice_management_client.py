import http.client
import json
from foglamp.common import logger
from foglamp.common.microservice_management_client import exceptions as client_exceptions

_logger = logger.setup(__name__)
_help = """
    -------------------------------------------------------------------------------
    | GET, POST       | /foglamp/service   (GET allows type | name filter)        |
    | DELETE          | /foglamp/service/{service-id}                             |
    | POST, DELETE    | /foglamp/interest                                         |
    -------------------------------------------------------------------------------
"""


class MicroserviceManagementClient(object):
    _management_client_conn = None

    def __init__(self, microservice_management_host, microservice_management_port):
        self._management_client_conn = http.client.HTTPConnection("{0}:{1}".format(microservice_management_host, microservice_management_port))

    def register_service(self, service_registration_payload):
        """ Registers a newly created microservice with the core service

        The core service will persist this information in memory rather than write it to the storage layer since it will
        change on every run of FogLAMP.


        :param service_registration_payload: A dict object describing the microservice and giving details of the
        management interface for that microservice
        :return: a JSON object containing the UUID of the newly registered service
        """
        self._management_client_conn.request(method='POST', url='/foglamp/service', body=json.dumps(service_registration_payload))
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
        self._management_client_conn.request(method='DELETE', url='/foglamp/service/{}'.format(microservice_id))
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

        payload = json.dumps({"category": category, "service": microservice_id})
        self._management_client_conn.request(method='POST', url='/foglamp/interest', body=payload)
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
        self._management_client_conn.request(method='DELETE', url='/foglamp/interest/{}'.format(registered_interest_id))
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

    def get_services(self, name=None, _type=None):
        """ Retrieve the details of one or more services that are registered

        :param name: filter the returned services by name
        :param _type: filter the returned services by type
        :return: list of registered microservices, all or based on filter(s) applied
        """
        url = '/foglamp/service'
        if _type:
            url = '{}?type={}'.format(url, _type)
        if name:
            url = '{}?name={}'.format(url, name)
        if name and _type:
            url = '{}?name={}&type={}'.format(url, name, _type)
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
