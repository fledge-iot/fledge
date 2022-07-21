import asyncio
from fledge.services.core import connect
from fledge.common.storage_client.payload_builder import PayloadBuilder
from fledge.common.storage_client.exceptions import StorageServerError


class ACLManagement:
    def __init__(self):
        self._storage_client = connect.get_storage_async()

    async def handle_update_for_acl_config_item(self, cat_name, config_item_list):
        for config_item in config_item_list:
            try:
                if config_item['type'] == 'ACL':
                    try:
                        # Note entity_type must be a service since it is a config item of type ACL
                        # in a category.
                        delete_payload = PayloadBuilder().WHERE(
                            ["name", "=", config_item["value"]]).payload()
                        result = await self._storage_client.delete_from_tbl("acl_usage", delete_payload)

                        payload = PayloadBuilder().INSERT(entity_name=cat_name,
                                                          entity_type="service",
                                                          name=config_item['value']).payload()
                        result = await self._storage.insert_into_tbl("acl_usage", payload)
                        response = result['response']
                    except KeyError:
                        raise ValueError(result['message'])
                    except StorageServerError as ex:
                        err_response = ex.error
                        raise ValueError(err_response)
            except KeyError:
                continue

    async def handle_delete_for_acl_config_item(self, category_name, config_item):
        payload = PayloadBuilder().SELECT("key", "value").WHERE(["key", "=", category_name]).payload()
        results = await self._storage_client.query_tbl_with_payload('configuration', payload)
        for row in results["rows"]:
            for item_name, item_info in row["value"].items():
                if item_name == config_item:
                    try:
                        # Note entity_type must be a service since it is a config item of type ACL
                        # in a category.
                        delete_payload = PayloadBuilder().WHERE(
                                                          ["name", "=", item_info["value"]]).payload()
                        result = await self._storage_client.delete_from_tbl("acl_usage", delete_payload)
                        response = result['response']
                    except KeyError:
                        raise ValueError(result['message'])
                    except StorageServerError as ex:
                        err_response = ex.error
                        raise ValueError(err_response)

    async def handle_create_for_acl_config_item(self, category_name, config_item):
        payload = PayloadBuilder().SELECT("key", "value").WHERE(["key", "=", category_name]).payload()
        results = await self._storage_client.query_tbl_with_payload('configuration', payload)
        for row in results["rows"]:
            for item_name, item_info in row["value"].items():
                if item_name == config_item:
                    try:
                        # Note entity_type must be a service since it is a config item of type ACL
                        # in a category.
                        payload = PayloadBuilder().INSERT(entity_name=category_name,
                                                          entity_type="service",
                                                          name=item_info['value']).payload()
                        result = await self._storage_client.insert_into_tbl("acl_usage", payload)
                        response = result['response']
                    except KeyError:
                        raise ValueError(result['message'])
                    except StorageServerError as ex:
                        err_response = ex.error
                        raise ValueError(err_response)
