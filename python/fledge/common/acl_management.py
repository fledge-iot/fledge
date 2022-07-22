import asyncio
import logging

from fledge.services.core import connect
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.exceptions import StorageServerError
from fledge.common.microservice_management_client import MicroserviceManagementClient
from fledge.python.fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.python.fledge.services.core.service_registry.service_registry.exceptions import DoesNotExist
from fledge.common import logger

_logger = logger.setup(__name__, level=logging.DEBUG)


class ACLManagement:
    def __init__(self):
        self._storage_client = connect.get_storage_async()

    async def handle_update_for_acl_usage(self, entity_name, acl_name_or_config_item, entity_type):
        if entity_type == "service":
            payload = PayloadBuilder().SELECT("key", "value").WHERE(["key", "=", entity_name]).payload()
            results = await self._storage_client.query_tbl_with_payload('configuration', payload)
            for row in results["rows"]:
                for item_name, item_info in row["value"].items():
                    if item_name == acl_name_or_config_item:
                        try:
                            required_name = item_info['value']
                            payload_update = PayloadBuilder().WHERE(["entity_type", "=", "service"]).\
                                ANDWHERE(["entity_name", "=", entity_name]).\
                                EXPR(["name", "=", required_name]).payload()

                            result = await self._storage_client.update_tbl("acl_usage", payload_update)
                            response = result['response']

                            # We need to find the address and management host for the required service.
                            try:
                                services = ServiceRegistry.get(name=entity_name)
                                service = services[0]
                            except DoesNotExist:  # Does not exist
                                _logger.error("Cannot notify the service {} "
                                              "about ACL Update.".format(entity_name))
                                return
                            else:
                                _logger.info("Notifying the service"
                                             " {} about ACL Update".format(entity_name))
                                mgt_client = MicroserviceManagementClient(service._address,
                                                                          service._management_port)
                                mgt_client.update_security_for_acl_change(acl=required_name,
                                                                          reason="updateACL")

                        except KeyError:
                            raise ValueError(result['message'])
                        except StorageServerError as ex:
                            err_response = ex.error
                            raise ValueError(err_response)
        else:
            try:
                required_name = acl_name_or_config_item
                payload_update = PayloadBuilder().WHERE(["entity_type", "=", "control"]). \
                    ANDWHERE(["entity_name", "=", entity_name]). \
                    EXPR(["name", "=", required_name]).payload()

                result = await self._storage_client.update_tbl("acl_usage", payload_update)
            except KeyError:
                raise ValueError(result['message'])
            except StorageServerError as ex:
                err_response = ex.error
                raise ValueError(err_response)

    async def handle_delete_for_acl_usage(self, entity_name, acl_name_or_config_item, entity_type):
        if entity_type == "service":
            try:
                # Note entity_type must be a service since it is a config item of type ACL
                # in a category.
                delete_payload = PayloadBuilder().WHERE(["entity_name", "=", entity_name]). \
                    ANDWHERE(["entity_type", "=", "service"]).payload()
                result = await self._storage_client.delete_from_tbl("acl_usage", delete_payload)
                response = result['response']

                payload = PayloadBuilder().SELECT("key", "value").WHERE(["key", "=", entity_name]).payload()
                results = await self._storage_client.query_tbl_with_payload('configuration', payload)
                for row in results["rows"]:
                    for item_name, item_info in row["value"].items():
                        if item_name == acl_name_or_config_item:
                            acl = item_info['value']
                # We need to find the address and management host for the required service.
                try:
                    services = ServiceRegistry.get(name=entity_name)
                    service = services[0]
                except DoesNotExist:  # Does not exist
                    # log and return
                    _logger.error("Cannot notify the service {} "
                                  "about ACL Detach.".format(entity_name))
                    return
                else:
                    _logger.info("Notifying the service"
                                 " {} about ACL Update".format(entity_name))
                    mgt_client = MicroserviceManagementClient(service._address,
                                                              service._management_port)
                    mgt_client.update_security_for_acl_change(acl=acl, reason="detachACL")
            except KeyError:
                raise ValueError(result['message'])
            except StorageServerError as ex:
                err_response = ex.error
                raise ValueError(err_response)
        else:
            try:
                # Note entity_type must be a script since ACL is being deleted.
                delete_payload = PayloadBuilder().WHERE(["name", "=", acl_name_or_config_item]). \
                    ANDWHERE(["entity_type", "=", "script"]).payload()
                result = await self._storage_client.delete_from_tbl("acl_usage", delete_payload)
                response = result['response']
            except KeyError:
                raise ValueError(result['message'])
            except StorageServerError as ex:
                err_response = ex.error
                raise ValueError(err_response)

    async def handle_create_for_acl_usage(self, entity_name, acl_name_or_config_item, entity_type):
        if entity_type == "service":

            payload = PayloadBuilder().SELECT("key", "value").WHERE(["key", "=", entity_name]).payload()
            results = await self._storage_client.query_tbl_with_payload('configuration', payload)
            for row in results["rows"]:
                for item_name, item_info in row["value"].items():
                    if item_name == acl_name_or_config_item:
                        try:
                            # Note entity_type must be a service since it is a config item of type ACL
                            # in a category.
                            acl = item_info['value']
                            payload = PayloadBuilder().INSERT(entity_name=entity_name,
                                                              entity_type="service",
                                                              name=item_info['value']).payload()
                            result = await self._storage_client.insert_into_tbl("acl_usage", payload)
                            response = result['response']
                            # We need to find the address and management host for the required service.
                            try:
                                services = ServiceRegistry.get(name=entity_name)
                                service = services[0]
                            except DoesNotExist:  # Does not exist
                                _logger.error("Cannot notify the service {} "
                                              "about ACL Attach.".format(entity_name))
                            else:
                                _logger.info("Notifying the service"
                                             " {} about ACL Attach".format(entity_name))
                                mgt_client = MicroserviceManagementClient(service._address,
                                                                          service._management_port)
                                mgt_client.update_security_for_acl_change(acl=acl, reason="attachACL")

                        except KeyError:
                            raise ValueError(result['message'])
                        except StorageServerError as ex:
                            err_response = ex.error
                            raise ValueError(err_response)
        else:
            try:
                # Note entity_type must be a script since handle new acl is called.
                acl_name = acl_name_or_config_item
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
