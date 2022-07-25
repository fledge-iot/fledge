import logging

from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.exceptions import StorageServerError


from fledge.common import logger

_logger = logger.setup(__name__, level=logging.DEBUG)


class ACLManagement(object):
    def __init__(self):
        from fledge.services.core import connect
        self._storage_client = connect.get_storage_async()

    def _notify_service_about_acl_change(self, entity_name, acl, reason):
        """Helper function that sends the ACL change to the respective service. """
        # We need to find the address and management host for the required service.
        from fledge.services.core.service_registry.service_registry import ServiceRegistry
        from fledge.services.core.service_registry.exceptions import DoesNotExist
        try:
            services = ServiceRegistry.get(name=entity_name)
            service = services[0]
        except DoesNotExist:  # Does not exist
            _logger.error("Cannot notify the service {} "
                          "about {}. It does not exist.".format(entity_name, reason))
            return
        else:
            _logger.info("Notifying the service"
                         " {} about {}".format(entity_name, reason))
            from fledge.common.microservice_management_client.microservice_management_client import MicroserviceManagementClient
            _logger.info("The host and port is {} {} and "
                         "entity is {}".format(service._address,
                                               service._management_port,
                                               entity_name))
            mgt_client = MicroserviceManagementClient(service._address,
                                                      service._management_port)
            _logger.info("Connect established with {} at {} and port {}".format(entity_name,
                                                                                service._address,
                                                                                service._management_port))
            mgt_client.update_service_for_acl_change_security(acl=acl,
                                                              reason=reason)
            _logger.info("Notified the {} about {}".format(entity_name, reason))

    async def handle_update_for_acl_usage(self, entity_name, acl_name, entity_type):
        if entity_type == "service":
            try:
                required_name = acl_name
                payload_update = PayloadBuilder().WHERE(["entity_type", "=", "service"]).\
                    AND_WHERE(["entity_name", "=", entity_name]).\
                    EXPR(["name", "=", required_name]).payload()

                result = await self._storage_client.update_tbl("acl_usage", payload_update)
                response = result['response']
                self._notify_service_about_acl_change(entity_name, required_name, "updateACL")
            except KeyError:
                raise ValueError(result['message'])
            except StorageServerError as ex:
                err_response = ex.error
                raise ValueError(err_response)
        else:
            try:
                required_name = acl_name
                payload_update = PayloadBuilder().WHERE(["entity_type", "=", "script"]). \
                    AND_WHERE(["entity_name", "=", entity_name]). \
                    EXPR(["name", "=", required_name]).payload()

                result = await self._storage_client.update_tbl("acl_usage", payload_update)
            except KeyError:
                raise ValueError(result['message'])
            except StorageServerError as ex:
                err_response = ex.error
                raise ValueError(err_response)

    async def handle_delete_for_acl_usage(self, entity_name, acl_name, entity_type):
        if entity_type == "service":
            try:
                # Note entity_type must be a service since it is a config item of type ACL
                # in a category.
                delete_payload = PayloadBuilder().WHERE(["entity_name", "=", entity_name]). \
                    AND_WHERE(["entity_type", "=", "service"]).payload()
                result = await self._storage_client.delete_from_tbl("acl_usage", delete_payload)
                response = result['response']

                self._notify_service_about_acl_change(entity_name, acl_name, "deleteACL")
            except KeyError:
                raise ValueError(result['message'])
            except StorageServerError as ex:
                err_response = ex.error
                raise ValueError(err_response)
        else:
            try:
                # Note entity_type must be a script since ACL is being deleted.
                delete_payload = PayloadBuilder().WHERE(["name", "=", acl_name]). \
                    AND_WHERE(["entity_type", "=", "script"]).payload()
                result = await self._storage_client.delete_from_tbl("acl_usage", delete_payload)
                response = result['response']
            except KeyError:
                raise ValueError(result['message'])
            except StorageServerError as ex:
                err_response = ex.error
                raise ValueError(err_response)

    async def handle_create_for_acl_usage(self, entity_name, acl_name, entity_type, notify_service=False):
        if entity_type == "service":
            try:
                # Note entity_type must be a service since it is a config item of type ACL
                # in a category.
                q_payload = PayloadBuilder().SELECT("name", "entity_name", "entity_type"). \
                    WHERE(["entity_name", "=", entity_name]). \
                    AND_WHERE(["entity_type", "=", entity_type]).\
                    AND_WHERE(["name", "=", ""]).payload()
                results = await self._storage_client.query_tbl_with_payload('acl_usage', q_payload)
                # Check if the value to insert already exists.
                if len(results["rows"]) > 0:
                    _logger.info("The tuple ({}, {}, {}) already exists in acl usage table.".format(entity_name,
                                                                                                    entity_type,
                                                                                                    acl_name))

                    payload_update = PayloadBuilder().WHERE(["entity_type", "=", "service"]). \
                        AND_WHERE(["name", "=", acl_name]).\
                        AND_WHERE(["entity_name", "=", entity_name]).\
                        EXPR(["name", "=", acl_name]).payload()

                    result = await self._storage_client.update_tbl("acl_usage", payload_update)
                    response = result['response']

                else:
                    payload = PayloadBuilder().INSERT(entity_name=entity_name,
                                                      entity_type="service",
                                                      name=acl_name).payload()
                    result = await self._storage_client.insert_into_tbl("acl_usage", payload)
                    response = result['response']

                if notify_service:
                    self._notify_service_about_acl_change(entity_name, acl_name, "attachACL")
            except KeyError:
                raise ValueError(result['message'])
            except StorageServerError as ex:
                err_response = ex.error
                raise ValueError(err_response)
        else:
            try:
                # Note entity_type must be a script since handle new acl is called.
                acl_name = acl_name
                payload = PayloadBuilder().INSERT(entity_name=entity_name,
                                                  entity_type="script",
                                                  name=acl_name).payload()
                result = await self._storage_client.insert_into_tbl("acl_usage", payload)
                response = result['response']
            except KeyError:
                raise ValueError(result['message'])
            except StorageServerError as ex:
                err_response = ex.error
                raise ValueError(err_response)
