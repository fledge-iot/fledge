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
	ServiceRecord *existing;
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
