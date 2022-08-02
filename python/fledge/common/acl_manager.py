import aiohttp

import logging

from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common import logger

_logger = logger.setup(__name__, level=logging.DEBUG)


class ACLManagerSingleton(object):
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state


class ACLManager(ACLManagerSingleton):
    _pending_notifications = {}
    _storage_client = None
    
    def __init__(self, given_client=None):
        ACLManagerSingleton.__init__(self)
        if not given_client:
            from fledge.services.core import connect
            self._storage_client = connect.get_storage_async()
        else:
            self._storage_client = given_client

    async def _notify_service_about_acl_change(self, entity_name, acl, reason):
        """Helper function that sends the ACL change to the respective service. """
        # We need to find the address and management host for the required service.
        from fledge.services.core.service_registry.service_registry import ServiceRegistry
        from fledge.services.core.service_registry.exceptions import DoesNotExist
        try:
            services = ServiceRegistry.get(name=entity_name)
            service = services[0]
        except DoesNotExist:  # Does not exist
            _logger.error("Cannot notify the service {} "
                          "about {}. It does not exist in service registry.".format(entity_name, reason))
            return
        else:
            try:
                _logger.info("Notifying the service"
                             " {} about {}".format(entity_name, reason))
                from fledge.common.service_record import ServiceRecord

                if service.Status == ServiceRecord.Status.Shutdown:
                    _logger.error("The service {} has failed. Cannot notify the service about ACL change.")
                    return

                elif service.Status == ServiceRecord.Status.Unresponsive:
                    _logger.warn("The service {} is Unresponsive. Skipping notifying "
                                 "the service about ACL change. But adding to pending items.")
                    _logger.info("Moved {} to pending. And pending items are {}".format(entity_name,
                                                                                        self._pending_notifications))
                    self._pending_notifications[entity_name] = acl
                    return

                elif service.Status == ServiceRecord.Status.Failed:
                    _logger.error("The service {} has failed. Cannot notify the service about ACL change")
                    return

                from fledge.common.microservice_management_client.microservice_management_client import MicroserviceManagementClient
                _logger.info("The host and port is {} {} and "
                             "entity is {}".format(service._address,
                                                   service._management_port,
                                                   entity_name))
                mgt_client = MicroserviceManagementClient(service._address,
                                                          service._management_port)
                _logger.info("Connection established with {} at {} and port {}".format(entity_name,
                                                                                    service._address,
                                                                                    service._management_port))
                await mgt_client.update_service_for_acl_change_security(acl=acl,
                                                                        reason=reason)
                _logger.info("Notified the {} about {}".format(entity_name, reason))
                # clearing the pending notifications if any.
                if entity_name in self._pending_notifications:
                    self._pending_notifications.pop(entity_name)

            except Exception as ex:
                _logger.error("Could not notify {} due to {}".format(entity_name, ex))

    async def handle_update_for_acl_usage(self, entity_name, acl_name, entity_type):
        _logger.debug("Update acl usage called for {} {} {}".format(entity_name, acl_name, entity_type))

        if entity_type == "service":
            try:
                del_payload = PayloadBuilder().WHERE(["entity_type", "=", "service"]). \
                    AND_WHERE(["entity_name", "=", entity_name]).payload()
                result = await self._storage_client.delete_from_tbl('acl_usage', del_payload)

                payload = PayloadBuilder().INSERT(entity_name=entity_name,
                                                  entity_type="service",
                                                  name=acl_name).payload()
                _logger.info("insert payload is {}".format(payload))
                result = await self._storage_client.insert_into_tbl("acl_usage", payload)
                response = result['response']

                await self._notify_service_about_acl_change(entity_name, acl_name, "reloadACL")
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

    async def handle_delete_for_acl_usage(self, entity_name, acl_name, entity_type, notify_service=True):
        _logger.debug("delete acl usage called for {} {} {}".format(entity_name, acl_name, entity_type))

        if entity_type == "service":
            try:
                # Note entity_type must be a service since it is a config item of type ACL
                # in a category.
                delete_payload = PayloadBuilder().WHERE(["entity_name", "=", entity_name]). \
                    AND_WHERE(["entity_type", "=", "service"]).payload()
                _logger.debug("The delete payload is {}".format(delete_payload))

                result = await self._storage_client.delete_from_tbl("acl_usage", delete_payload)
                response = result['response']
                _logger.debug("The response payload is {}".format(response))

                if notify_service:
                    await self._notify_service_about_acl_change(entity_name,
                                                                acl_name,
                                                                "detachACL")
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

    async def handle_create_for_acl_usage(self, entity_name, acl_name, entity_type, notify_service=False,
                                          acl_to_delete=None):
        _logger.debug("Create acl usage called for {} {} {}".format(entity_name, acl_name, entity_type))
        if entity_type == "service":
            try:
                # Note entity_type must be a service since it is a config item of type ACL
                # in a category.
                _logger.debug("Notify south is {}".format(notify_service))
                q_payload = PayloadBuilder().SELECT("name", "entity_name", "entity_type"). \
                    WHERE(["entity_name", "=", entity_name]). \
                    AND_WHERE(["entity_type", "=", entity_type]).\
                    AND_WHERE(["name", "=", acl_name]).payload()
                results = await self._storage_client.query_tbl_with_payload('acl_usage', q_payload)
                _logger.debug("The result of query is {}".format(results))
                # Check if the value to insert already exists.
                if len(results["rows"]) > 0:
                    _logger.debug("The tuple ({}, {}, {}) already exists in acl usage table.".format(entity_name,
                                                                                                    entity_type,
                                                                                                    acl_name))
                else:
                    payload = PayloadBuilder().INSERT(entity_name=entity_name,
                                                      entity_type="service",
                                                      name=acl_name).payload()
                    result = await self._storage_client.insert_into_tbl("acl_usage", payload)
                    response = result['response']
                    if acl_to_delete is not None:
                        delete_payload = PayloadBuilder().WHERE(["entity_name", "=", entity_name]). \
                            AND_WHERE(["entity_type", "=", entity_type]).\
                            AND_WHERE(["name", "=", acl_to_delete]).payload()
                        _logger.debug("The acl to delete is {} and entity name is {}".format(acl_to_delete,
                                                                                            entity_name))
                        result = await self._storage_client.delete_from_tbl("acl_usage", delete_payload)
                        response = result['response']
                        _logger.debug("the response is {}".format(response))

                if notify_service:
                    await self._notify_service_about_acl_change(entity_name, acl_name, "attachACL")
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

    async def get_all_entities_for_a_acl(self, acl_name, entity_type):
        """Get all the entities attached to an acl."""
        q_payload = PayloadBuilder().SELECT("entity_name"). \
            AND_WHERE(["entity_type", "=", entity_type]). \
            AND_WHERE(["name", "=", acl_name]).payload()
        results = await self._storage_client.query_tbl_with_payload('acl_usage', q_payload)

        if len(results['rows']) > 0:
            entities = []
            for row in results['rows']:
                entities.append(row['entity_name'])
            return entities
        else:
            return []

    async def get_acl_for_an_entity(self, entity_name, entity_type):
        """Get the acl attached to an entity."""
        q_payload = PayloadBuilder().SELECT("name"). \
            AND_WHERE(["entity_type", "=", entity_type]). \
            AND_WHERE(["entity_name", "=", entity_name]).payload()
        results = await self._storage_client.query_tbl_with_payload('acl_usage', q_payload)

        if len(results['rows']) > 0:
            for row in results['rows']:
                return row['name']
        else:
            return ""

    async def resolve_pending_notification_for_acl_change(self, svc_name):
        """Methods that handles the pending notification about acl change to the service."""
        _logger.debug("svc name {} and pending notifications {}".format(svc_name,
                                                                       self._pending_notifications))
        if svc_name not in self._pending_notifications:
            return

        new_acl = await self.get_acl_for_an_entity(svc_name, "service")
        old_acl = self._pending_notifications[svc_name]

        _logger.debug("new acl is {} old acl is {}".format(new_acl, old_acl))
        if new_acl == old_acl and new_acl != "":
            await self._notify_service_about_acl_change(entity_name=svc_name, acl=new_acl,
                                                        reason="reloadACL")

        if old_acl != "" and new_acl == "":
            await self._notify_service_about_acl_change(entity_name=svc_name, acl=new_acl,
                                                        reason="detachACL")

        if old_acl == "" and new_acl != "":
            await self._notify_service_about_acl_change(entity_name=svc_name, acl=new_acl,
                                                        reason="attachACL")
