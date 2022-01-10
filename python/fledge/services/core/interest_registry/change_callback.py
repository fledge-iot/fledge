# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Module to hold the callback to notify microservices of config changes. """

import json
import asyncio
import aiohttp
from fledge.common.configuration_manager import ConfigurationManager
from fledge.services.core.service_registry.service_registry import ServiceRegistry
from fledge.services.core.service_registry import exceptions as service_registry_exceptions
from fledge.services.core.interest_registry.interest_registry import InterestRegistry
from fledge.services.core.interest_registry import exceptions as interest_registry_exceptions
from fledge.common import logger

__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

_LOGGER = logger.setup(__name__)


async def run(category_name):
    """ Callback run by configuration category to notify changes to interested microservices

    Note: this method is async as needed

    Args:
        configuration_name (str): name of category that was changed
    """

    # get all interest records regarding category_name
    cfg_mgr = ConfigurationManager()
    interest_registry = InterestRegistry(cfg_mgr)
    try:
        interest_records = interest_registry.get(category_name=category_name)
    except interest_registry_exceptions.DoesNotExist:
        return

    category_value = await cfg_mgr.get_category_all_items(category_name)
    payload = {"category" : category_name, "items" : category_value}
    headers = {'content-type': 'application/json'}

    # for each microservice interested in category_name, notify change
    for i in interest_records:
        # get microservice management server info of microservice through service registry
        try: 
            service_record = ServiceRegistry.get(idx=i._microservice_uuid)[0]
        except service_registry_exceptions.DoesNotExist:
            _LOGGER.exception("Unable to notify microservice with uuid %s as it is not found in the service registry", i._microservice_uuid)
            continue
        url = "{}://{}:{}/fledge/change".format(service_record._protocol, service_record._address, service_record._management_port)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, data=json.dumps(payload, sort_keys=True), headers=headers) as resp:
                    result = await resp.text()
                    status_code = resp.status
                    if status_code in range(400, 500):
                        _LOGGER.error("Bad request error code: %d, reason: %s", status_code, resp.reason)
                    if status_code in range(500, 600):
                        _LOGGER.error("Server error code: %d, reason: %s", status_code, resp.reason)
            except Exception as ex:
                _LOGGER.exception("Unable to notify microservice with uuid %s due to exception: %s", i._microservice_uuid, str(ex))
                continue


async def run_child_create(parent_category_name, child_category_list):
    """ Call the child_create Management API

    Args:
        parent_category_name (str): parent category of the children one
        child_category_list (str): list of the children category changed
    """

    # get all interest records regarding category_name
    cfg_mgr = ConfigurationManager()
    interest_registry = InterestRegistry(cfg_mgr)
    try:
        interest_records = interest_registry.get(category_name=parent_category_name)
    except interest_registry_exceptions.DoesNotExist:
        return


    #// FIXME_I:
    import logging


    #// FIXME_I:
    _LOGGER.setLevel(logging.DEBUG)
    _LOGGER.debug("xxx5 run_child_create parent_category_name :{}: child_category_list :{}:".format(parent_category_name, child_category_list ) )
    _LOGGER.setLevel(logging.WARNING)

    #// FIXME_I:
    for child_category in child_category_list:

        category_value = await cfg_mgr.get_category_all_items(child_category)
        payload = {"parent_category" : parent_category_name, "category" : child_category, "items" : category_value}
        headers = {'content-type': 'application/json'}

        # for each microservice interested in category_name, notify change
        for i in interest_records:
            # get microservice management server info of microservice through service registry
            try:
                service_record = ServiceRegistry.get(idx=i._microservice_uuid)[0]
            except service_registry_exceptions.DoesNotExist:
                _LOGGER.exception("Unable to notify microservice with uuid %s as it is not found in the service registry", i._microservice_uuid)
                continue
            url = "{}://{}:{}/fledge/child_create".format(service_record._protocol, service_record._address, service_record._management_port)

            #// FIXME_I:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.debug("xxx5 run_child_create url :{}: ".format(url) )
            _LOGGER.setLevel(logging.WARNING)

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(url, data=json.dumps(payload, sort_keys=True), headers=headers) as resp:
                        result = await resp.text()
                        status_code = resp.status
                        if status_code in range(400, 500):
                            _LOGGER.error("Bad request error code: %d, reason: %s", status_code, resp.reason)
                        if status_code in range(500, 600):
                            _LOGGER.error("Server error code: %d, reason: %s", status_code, resp.reason)
                except Exception as ex:
                    _LOGGER.exception("Unable to notify microservice with uuid %s due to exception: %s", i._microservice_uuid, str(ex))
                    continue

async def run_child_delete(parent_category_name, child_category_list):
    """ Call the child_delete Management API

    Args:
        parent_category_name (str): parent category of the children one
        child_category_list (str): list of the children category changed
    """

    # get all interest records regarding category_name
    cfg_mgr = ConfigurationManager()
    interest_registry = InterestRegistry(cfg_mgr)
    try:
        interest_records = interest_registry.get(category_name=parent_category_name)
    except interest_registry_exceptions.DoesNotExist:
        return

    #// FIXME_I:
    import logging


    #// FIXME_I:
    _LOGGER.setLevel(logging.DEBUG)
    _LOGGER.debug("xxx7 run_child_delete parent_category_name :{}: child_category_list :{}:".format(parent_category_name, child_category_list ) )
    _LOGGER.setLevel(logging.WARNING)

    #// FIXME_I:
    for child_category in child_category_list:

        #// FIXME_I:
        category_value = await cfg_mgr.get_category_all_items(child_category)
        payload = {"parent_category" : parent_category_name, "category" : child_category, "items" : category_value}
        headers = {'content-type': 'application/json'}

        # for each microservice interested in category_name, notify change
        for i in interest_records:
            # get microservice management server info of microservice through service registry
            try:
                service_record = ServiceRegistry.get(idx=i._microservice_uuid)[0]
            except service_registry_exceptions.DoesNotExist:
                _LOGGER.exception("Unable to notify microservice with uuid %s as it is not found in the service registry", i._microservice_uuid)
                continue
            url = "{}://{}:{}/fledge/child_delete".format(service_record._protocol, service_record._address, service_record._management_port)

            #// FIXME_I:
            _LOGGER.setLevel(logging.DEBUG)
            _LOGGER.debug("xxx5 run_child_delete url :{}: ".format(url) )
            _LOGGER.setLevel(logging.WARNING)

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(url, data=json.dumps(payload, sort_keys=True), headers=headers) as resp:
                        result = await resp.text()
                        status_code = resp.status
                        if status_code in range(400, 500):
                            _LOGGER.error("Bad request error code: %d, reason: %s", status_code, resp.reason)
                        if status_code in range(500, 600):
                            _LOGGER.error("Server error code: %d, reason: %s", status_code, resp.reason)
                except Exception as ex:
                    _LOGGER.exception("Unable to notify microservice with uuid %s due to exception: %s", i._microservice_uuid, str(ex))
                    continue




async def run_child(parent_category_name, child_category_list, operation):
    """ Callback run by configuration category to notify changes to interested microservices

    Note: this method is async as needed

    Args:
        parent_category_name (str): parent category of the children one
        child_category_list (str): list of the children category changed
        operation (str): "c" = created | "d" = delete
    """

    #// FIXME_I:
    import logging


    #// FIXME_I:
    _LOGGER.setLevel(logging.DEBUG)
    _LOGGER.debug("xxx5 run_child :{}: -".format(operation) )
    _LOGGER.setLevel(logging.WARNING)

    if operation == "c":
        await run_child_create (parent_category_name, child_category_list)
    elif operation == "d":
        await run_child_delete (parent_category_name, child_category_list)
    else:
        _LOGGER.error("Requested operation not supported only create/delete are supported, quested operation %s", operation)

