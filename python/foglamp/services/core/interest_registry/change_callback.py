import json
import asyncio
import aiohttp
from foglamp.common.configuration_manager import ConfigurationManager
from foglamp.services.core.service_registry.service_registry import ServiceRegistry
from foglamp.services.core.service_registry import exceptions as service_registry_exceptions
from foglamp.services.core.interest_registry.interest_registry import InterestRegistry
from foglamp.services.core.interest_registry import exceptions as interest_registry_exceptions
from foglamp.common import logger
_LOGGER = logger.setup(__name__)


async def run(category_name):
    cfg_mgr = ConfigurationManager()
    interest_registry = InterestRegistry(cfg_mgr)
    try:
        interest_records = interest_registry.get(category_name=category_name)
    except interest_registry_exceptions.DoesNotExist:
        return
    category_value = await cfg_mgr.get_category_all_items(category_name)
    payload = {"category" : category_name, "items" : category_value}
    headers = {'content-type': 'application/json'}
    for i in interest_records:
        try: 
            service_record = ServiceRegistry.get(idx=i._microservice_uuid)[0]
        except service_registry_exceptions.DoesNotExist:
            continue
        url = "{}://{}:{}/foglamp/change".format(service_record._protocol, service_record._address, service_record._management_port)
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, data=json.dumps(payload), headers=headers) as resp:
                    result = await resp.text()
                    status_code = resp.status
                    if status_code in range(400, 500):
                        _LOGGER.error("Bad request error code: %d, reason: %s", status_code, resp.reason)
                    if status_code in range(500, 600):
                        _LOGGER.error("Server error code: %d, reason: %s", status_code, resp.reason)
            except:
                continue
