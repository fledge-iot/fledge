import http.client
import json
from foglamp.common import logger
from foglamp.common.microservice_management_client import exceptions as client_exceptions

_logger = logger.setup(__name__)

class MicroserviceManagementClient(object):
    _management_client_conn = None

    def __init__(self, microservice_management_host, microservice_management_port):
        self._management_client_conn = http.client.HTTPConnection("{0}:{1}".format(microservice_management_host, microservice_management_port))

    def register_service(self, service_registration_payload):
        self._management_client_conn.request(method='POST', url='/foglamp/service', body=json.dumps(service_registration_payload))
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d", r.status)
            raise client_exceptions.MicroserviceManagementClientError
        if r.status in range(500, 600):
            _logger.error("Client error code: %d", r.status)
            raise client_exceptions.MicroserviceManagementClientError
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        try:
            response["id"]
        except KeyError:
            error = response["error"]
            _logger.exception("Could not register the microservice, From request %s, Got error %s", json.dumps(service_registration_payload), error)
        except Exception as ex:
            _logger.exception("Could not register the microservice, From request %s, Reason: %s", json.dumps(service_registration_payload), str(ex))
            raise

        return response

    def unregister_service(self, microservice_id):
        self._management_client_conn.request(method='DELETE', url='/foglamp/service/{}'.format(microservice_id))
        r = self._management_client_conn.getresponse()
        if r.status in range(400, 500):
            _logger.error("Client error code: %d", r.status)
            raise client_exceptions.MicroserviceManagementClientError
        if r.status in range(500, 600):
            _logger.error("Client error code: %d", r.status)
            raise client_exceptions.MicroserviceManagementClientError
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        try:
            response["id"]
        except KeyError:
            error = response["error"]
            _logger.exception("Could not un-register the micro-service having uuid %s, "
                              "Got error: %s", microservice_id, error)
        except Exception as ex:
            _logger.exception("Could not un-register the micro-service having uuid %s, "
                              "Reason: %s", microservice_id, str(ex))
            raise

        return response

    def register_interest(self):
        pass

    def unregister_interest(self):
        pass

    def get_services(self, name=None, _type=None):
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
            _logger.error("Client error code: %d", r.status)
            raise client_exceptions.MicroserviceManagementClientError
        if r.status in range(500, 600):
            _logger.error("Client error code: %d", r.status)
            raise client_exceptions.MicroserviceManagementClientError
        res = r.read().decode()
        self._management_client_conn.close()
        response = json.loads(res)
        try:
            response["services"]
        except KeyError:
            error = response["error"]
            _logger.exception("Could not find the micro-service for request url %s, Got error: %s", url, error)
        except Exception as ex:
            _logger.exception("Could not find the micro-service for request url %s, Reason: %s", url, str(ex))
            raise

        return response
