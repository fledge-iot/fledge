import asyncio
from fledge.services.core import connect
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.exceptions import StorageServerError


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
                            payload = PayloadBuilder().INSERT(entity_name=entity_name,
                                                              entity_type="service",
                                                              name=item_info['value']).payload()
                            result = await self._storage_client.insert_into_tbl("acl_usage", payload)
                            response = result['response']
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
