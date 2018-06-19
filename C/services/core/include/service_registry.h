#ifndef _SERVICE_REGISTRY_H
#define _SERVICE_REGISTRY_H
/*
 * FogLAMP service registry.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <service_record.h>
#include <vector>
#include <string>

/**
 * ServiceRegistry Singleton class
 */
class ServiceRegistry {
	public:
		static ServiceRegistry		*getInstance();
		bool				registerService(ServiceRecord *service);
		bool				unRegisterService(ServiceRecord *service);
		ServiceRecord			*findService(const std::string& name);
	private:
		ServiceRegistry();
		~ServiceRegistry();
		static	ServiceRegistry		*m_instance;
		std::vector<ServiceRecord *>	m_services;
};

#endif
