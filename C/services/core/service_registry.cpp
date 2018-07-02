/*
 * FogLAMP service registry.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <service_registry.h>
#include <uuid/uuid.h>

using namespace std;

ServiceRegistry *ServiceRegistry::m_instance = 0;

/**
 * Create the service registry singleton class
 */
ServiceRegistry::ServiceRegistry()
{
}

/**
 * Destroy the service registry singleton class
 */
ServiceRegistry::~ServiceRegistry()
{
	for (vector<ServiceRecord *>::iterator it = m_services.begin();
		it != m_services.end(); ++it)
	{
		delete *it;
	}
}

/**
 * Return the singleton instance of the service registry
 */
ServiceRegistry *ServiceRegistry::getInstance()
{
	if (m_instance == 0)
		m_instance = new ServiceRegistry();
	return m_instance;
}

/**
 * Register a service with the service registry
 *
 * @param service	The service to register
 * @return bool		True if the service was registered
 */
bool ServiceRegistry::registerService(ServiceRecord *service)
{
uuid_t		uuid;
char		uuid_str[37];
ServiceRecord	*existing;

	if ((existing = findService(service->getName())) != 0)
	{
		if (existing->getAddress().compare(service->getAddress()) ||
			existing->getType().compare(service->getType()) ||
			existing->getPort() != service->getPort())
		{
			/* Service already registered with the same name on
			 * a different address, port or type
			 */
			return false;
		}
		// Overwrite existing service
		unRegisterService(existing);
	}
	m_services.push_back(service);
	uuid_generate_time_safe(uuid);
	uuid_unparse_lower(uuid, uuid_str);
	m_uuids[string(uuid_str)] = service;
	return true;
}

/**
 * Unregister a service with the service registry
 *
 * @param service	The service to unregister
 * @return bool		True if the service was unregistered
 */
bool ServiceRegistry::unRegisterService(ServiceRecord *service)
{
	for (vector<ServiceRecord *>::iterator it = m_services.begin();
		it != m_services.end(); ++it)
	{
		if (*service == **it)
		{
			m_services.erase(it);
			for (map<string, ServiceRecord *>::iterator uit = m_uuids.begin(); uit != m_uuids.end(); ++ uit)
			{
				if (uit->second == service)
				{
					m_uuids.erase(uit);
					break;
				}
			}
			return true;
		}
	}
	return false;
}

/**
 * Unregister a service with the service registry
 *
 * @param uuid		The uuid of the service to unregister
 * @return bool		True if the service was unregistered
 */
bool ServiceRegistry::unRegisterService(const string& uuid)
{
ServiceRecord	*service;
map<string, ServiceRecord *>::iterator	uuidIt;
	
	if ((uuidIt = m_uuids.find(uuid)) == m_uuids.end())
	{
		return false;
	}
	service = m_uuids[uuid];
	for (vector<ServiceRecord *>::iterator it = m_services.begin();
		it != m_services.end(); ++it)
	{
		if (*service == **it)
		{
			m_services.erase(it);
			m_uuids.erase(uuidIt);
			return true;
		}
	}
	return false;
}

/**
 * Find a service that is registered with the service registry
 *
 * @param name		The name of the service to find
 * @return ServiceRecord*	The service record or null if not found
 */
ServiceRecord *ServiceRegistry::findService(const string& name)
{
	for (vector<ServiceRecord *>::iterator it = m_services.begin();
		it != m_services.end(); ++it)
	{
		if ((*it)->getName().compare(name) == 0)
			return *it;
	}
	return 0;
}

/**
 * Return the uuid of the registration record for a given service
 *
 * @param	service	The service to return the uuid for
 * @return string	The uud of the service registration
 * @throws eception	If the service could not be found
 */
string ServiceRegistry::getUUID(ServiceRecord *service)
{
map<string, ServiceRecord *>::const_iterator  it;

	for (it = m_uuids.cbegin(); it != m_uuids.cend(); ++it)
	{
		if (it->second == service)
		{
			return it->first;
		}
	}
	throw new exception();
}
